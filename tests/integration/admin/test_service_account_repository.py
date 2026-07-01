"""Integration tests for ServiceAccountRepository against real PostgreSQL."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from jentic_one.admin.core.schema.service_accounts import ServiceAccount
from jentic_one.admin.core.schema.users import User
from jentic_one.admin.repos import ServiceAccountRepository, UserRepository
from jentic_one.admin.services.errors import ServiceAccountNotFoundError
from jentic_one.shared.db.session import DatabaseSession
from jentic_one.shared.models import ActorStatus

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_service_accounts(admin_db: DatabaseSession) -> AsyncGenerator[None, None]:
    async with admin_db.session() as session:
        await session.execute(delete(ServiceAccount))
        await session.execute(delete(User))
        await session.commit()
    yield
    async with admin_db.session() as session:
        await session.execute(delete(ServiceAccount))
        await session.execute(delete(User))
        await session.commit()


@pytest.fixture()
async def test_owner(admin_db: DatabaseSession, clean_service_accounts: None) -> str:
    async with admin_db.session() as session:
        user = await UserRepository.create(
            session,
            email="sva-owner@example.com",
            first_name="SVA",
            last_name="Owner",
            created_by="usr_test",
        )
        await session.commit()
        return user.id


async def test_create_service_account(admin_db: DatabaseSession, test_owner: str) -> None:
    async with admin_db.session() as session:
        sva = await ServiceAccountRepository.create(
            session,
            name="test-sva",
            owner_id=test_owner,
            registered_by=test_owner,
            description="A test service account",
            created_by="usr_test",
        )
        await session.commit()
        assert sva.id.startswith("sva_")
        assert sva.name == "test-sva"
        assert sva.description == "A test service account"
        assert sva.owner_id == test_owner
        assert sva.status == "pending"


async def test_get_by_id(admin_db: DatabaseSession, test_owner: str) -> None:
    async with admin_db.session() as session:
        sva = await ServiceAccountRepository.create(
            session,
            name="lookup-sva",
            owner_id=test_owner,
            registered_by=test_owner,
            created_by="usr_test",
        )
        await session.commit()
        sva_id = sva.id

    async with admin_db.session() as session:
        loaded = await ServiceAccountRepository.get_by_id(session, sva_id)
        assert loaded is not None
        assert loaded.name == "lookup-sva"


async def test_get_by_id_not_found(admin_db: DatabaseSession, test_owner: str) -> None:
    async with admin_db.session() as session:
        loaded = await ServiceAccountRepository.get_by_id(session, "sva_nonexistent0000000000000")
        assert loaded is None


async def test_list_by_owner(admin_db: DatabaseSession, test_owner: str) -> None:
    async with admin_db.session() as session:
        user2 = await UserRepository.create(
            session,
            email="sva-owner2@example.com",
            first_name="SVA2",
            last_name="Owner2",
            created_by="usr_test",
        )
        await session.commit()
        user2_id = user2.id

    async with admin_db.session() as session:
        await ServiceAccountRepository.create(
            session,
            name="sva-a",
            owner_id=test_owner,
            registered_by=test_owner,
            created_by="usr_test",
        )
        await ServiceAccountRepository.create(
            session,
            name="sva-b",
            owner_id=test_owner,
            registered_by=test_owner,
            created_by="usr_test",
        )
        await ServiceAccountRepository.create(
            session, name="sva-c", owner_id=user2_id, registered_by=user2_id, created_by="usr_test"
        )
        await session.commit()

    async with admin_db.session() as session:
        owner1_svas = await ServiceAccountRepository.list_by_owner(session, test_owner)
        assert len(owner1_svas) == 2
        assert all(s.owner_id == test_owner for s in owner1_svas)

        owner2_svas = await ServiceAccountRepository.list_by_owner(session, user2_id)
        assert len(owner2_svas) == 1
        assert owner2_svas[0].name == "sva-c"


async def test_list_all_with_status_filter(admin_db: DatabaseSession, test_owner: str) -> None:
    async with admin_db.session() as session:
        await ServiceAccountRepository.create(
            session,
            name="pending-sva",
            owner_id=test_owner,
            registered_by=test_owner,
            created_by="usr_test",
        )
        s2 = await ServiceAccountRepository.create(
            session,
            name="active-sva",
            owner_id=test_owner,
            registered_by=test_owner,
            created_by="usr_test",
        )
        await session.flush()
        s2.status = "active"
        await session.flush()
        await session.commit()

    async with admin_db.session() as session:
        all_svas = await ServiceAccountRepository.list_all(session)
        assert len(all_svas) == 2

        pending = await ServiceAccountRepository.list_all(session, status="pending")
        assert len(pending) == 1
        assert pending[0].name == "pending-sva"

        active = await ServiceAccountRepository.list_all(session, status="active")
        assert len(active) == 1
        assert active[0].name == "active-sva"


async def test_set_approval(admin_db: DatabaseSession, test_owner: str) -> None:
    async with admin_db.session() as session:
        sva = await ServiceAccountRepository.create(
            session,
            name="approval-sva",
            owner_id=test_owner,
            registered_by=test_owner,
            created_by="usr_test",
        )
        await session.commit()
        sva_id = sva.id

    async with admin_db.session() as session:
        approved = await ServiceAccountRepository.set_approval(
            session, sva_id, approved_by=test_owner
        )
        await session.commit()
        assert approved.status == "active"
        assert approved.approved_by == test_owner
        assert approved.approved_at is not None


async def test_set_denial(admin_db: DatabaseSession, test_owner: str) -> None:
    async with admin_db.session() as session:
        sva = await ServiceAccountRepository.create(
            session,
            name="denied-sva",
            owner_id=test_owner,
            registered_by=test_owner,
            created_by="usr_test",
        )
        await session.commit()
        sva_id = sva.id

    async with admin_db.session() as session:
        denied = await ServiceAccountRepository.set_denial(
            session, sva_id, reason="Not authorized", denied_by=test_owner
        )
        await session.commit()
        assert denied.status == "rejected"
        assert denied.denial_reason == "Not authorized"
        assert denied.denied_by == test_owner


async def test_update_status_not_found(admin_db: DatabaseSession, test_owner: str) -> None:
    async with admin_db.session() as session:
        with pytest.raises(ServiceAccountNotFoundError):
            await ServiceAccountRepository.update_status(
                session, "sva_nonexistent0000000000000", ActorStatus.ACTIVE
            )


async def test_owner_fk_enforcement(admin_db: DatabaseSession, test_owner: str) -> None:
    async with admin_db.session() as session:
        with pytest.raises(IntegrityError):
            await ServiceAccountRepository.create(
                session,
                name="orphan-sva",
                owner_id="usr_nonexistent000000000000",
                registered_by=test_owner,
                created_by="usr_test",
            )
