"""Profile-related endpoints. Currently: bank accounts CRUD."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import current_user
from app.db.session import get_db
from app.models import BankAccount, User
from app.schemas.profile import BankAccountCreate, BankAccountOut
from app.utils.crypto import encrypt_field

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/bank-accounts", response_model=list[BankAccountOut])
async def list_bank_accounts(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BankAccountOut]:
    result = await db.execute(
        select(BankAccount)
        .where(BankAccount.user_id == user.id)
        .order_by(BankAccount.is_primary.desc(), BankAccount.created_at.asc())
    )
    rows = result.scalars().all()
    return [BankAccountOut.model_validate(r) for r in rows]


@router.post("/bank-accounts", response_model=BankAccountOut, status_code=status.HTTP_201_CREATED)
async def add_bank_account(
    body: BankAccountCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> BankAccountOut:
    # If this is the user's first account, force it primary regardless of input.
    existing = await db.execute(
        select(BankAccount).where(BankAccount.user_id == user.id)
    )
    has_any = existing.scalars().first() is not None
    is_primary = True if not has_any else body.is_primary

    if is_primary:
        # Demote any current primary first to keep the partial unique index happy.
        await db.execute(
            update(BankAccount)
            .where(BankAccount.user_id == user.id, BankAccount.is_primary.is_(True))
            .values(is_primary=False)
        )

    row = BankAccount(
        user_id=user.id,
        account_number_encrypted=encrypt_field(body.account_number),
        account_last4=body.account_number[-4:],
        ifsc=body.ifsc,
        bank_name=body.bank_name,
        account_type=body.account_type,
        is_primary=is_primary,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return BankAccountOut.model_validate(row)


@router.delete("/bank-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank_account(
    account_id: UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(BankAccount).where(BankAccount.id == account_id, BankAccount.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Bank account not found")
    was_primary = row.is_primary
    await db.delete(row)
    await db.flush()

    # If we just removed the primary, promote the oldest remaining account, if any.
    if was_primary:
        next_row = await db.execute(
            select(BankAccount)
            .where(BankAccount.user_id == user.id)
            .order_by(BankAccount.created_at.asc())
            .limit(1)
        )
        promoted = next_row.scalar_one_or_none()
        if promoted is not None:
            promoted.is_primary = True

    await db.commit()


@router.patch("/bank-accounts/{account_id}/make-primary", response_model=BankAccountOut)
async def make_primary(
    account_id: UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> BankAccountOut:
    result = await db.execute(
        select(BankAccount).where(BankAccount.id == account_id, BankAccount.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Bank account not found")
    if row.is_primary:
        return BankAccountOut.model_validate(row)

    # Demote current primary first to satisfy the partial unique index.
    await db.execute(
        update(BankAccount)
        .where(BankAccount.user_id == user.id, BankAccount.is_primary.is_(True))
        .values(is_primary=False)
    )
    await db.flush()
    row.is_primary = True
    await db.commit()
    await db.refresh(row)
    return BankAccountOut.model_validate(row)
