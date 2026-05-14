from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.contractor_repository import ContractorRepository
from swm_db.models import ContractorORM, RouteORM, WardORM
from swm_db.route_repository import RouteRepository
from swm_db.ward_repository import WardRepository


def _mock_session() -> MagicMock:
    ses = MagicMock(spec=AsyncSession)
    ses.execute = AsyncMock()
    ses.flush = AsyncMock()
    ses.refresh = AsyncMock()
    ses.delete = AsyncMock()
    ses.add = MagicMock()
    ses.add_all = MagicMock()
    return ses


def _scalar_result(value: Any) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalars.return_value.all.return_value = value if isinstance(value, list) else [value]
    return result


def _contractor(**kwargs: Any) -> ContractorORM:
    obj = ContractorORM(
        contractor_code=kwargs.pop("contractor_code", "CTR-001"),
        contractor_name=kwargs.pop("contractor_name", "Contractor A"),
        sla_details=kwargs.pop("sla_details", {}),
        **kwargs,
    )
    if obj.id is None:  # type: ignore[attr-defined]
        obj.id = uuid.uuid4()
    return obj


def _ward(**kwargs: Any) -> WardORM:
    obj = WardORM(
        ward_code=kwargs.pop("ward_code", "WARD-01"),
        ward_name=kwargs.pop("ward_name", "Ward One"),
        zone_name=kwargs.pop("zone_name", "North"),
        **kwargs,
    )
    if obj.id is None:  # type: ignore[attr-defined]
        obj.id = uuid.uuid4()
    return obj


def _route(**kwargs: Any) -> RouteORM:
    obj = RouteORM(
        route_code=kwargs.pop("route_code", "ROUTE-01"),
        route_name=kwargs.pop("route_name", "Route One"),
        expected_distance_km=kwargs.pop("expected_distance_km", 10.5),
        expected_duration_min=kwargs.pop("expected_duration_min", 35),
        start_point=kwargs.pop("start_point", "Depot A"),
        end_point=kwargs.pop("end_point", "Depot B"),
        **kwargs,
    )
    if obj.id is None:  # type: ignore[attr-defined]
        obj.id = uuid.uuid4()
    return obj


class TestContractorRepository:
    @pytest.mark.asyncio
    async def test_create_and_get_by_code(self) -> None:
        ses = _mock_session()
        repo = ContractorRepository(ses)
        created = await repo.create(
            contractor_code="CTR-100",
            contractor_name="Contractor 100",
            contact="ops@example.com",
            sla_details={"pickup": "4h"},
        )
        ses.add.assert_called_once()
        ses.flush.assert_awaited_once()
        ses.refresh.assert_awaited_once_with(created)

    @pytest.mark.asyncio
    async def test_update_missing_raises(self) -> None:
        ses = _mock_session()
        ses.execute.return_value = _scalar_result(None)
        with pytest.raises(NoResultFound):
            await ContractorRepository(ses).update(uuid.uuid4(), contractor_name="X")


class TestWardRepository:
    @pytest.mark.asyncio
    async def test_get_by_code_returns_row(self) -> None:
        ses = _mock_session()
        ward = _ward()
        ses.execute.return_value = _scalar_result(ward)
        result = await WardRepository(ses).get_by_code("ward-01")
        assert result is ward

    @pytest.mark.asyncio
    async def test_delete_calls_session_delete(self) -> None:
        ses = _mock_session()
        ward = _ward()
        ses.execute.return_value = _scalar_result(ward)
        await WardRepository(ses).delete(ward.id)
        ses.delete.assert_awaited_once_with(ward)


class TestRouteRepository:
    @pytest.mark.asyncio
    async def test_list_returns_rows(self) -> None:
        ses = _mock_session()
        routes = [_route(route_code="R1"), _route(route_code="R2")]
        ses.execute.return_value = _scalar_result(routes)
        items = await RouteRepository(ses).list()
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_update_missing_raises(self) -> None:
        ses = _mock_session()
        ses.execute.return_value = _scalar_result(None)
        with pytest.raises(NoResultFound):
            await RouteRepository(ses).update(uuid.uuid4(), route_name="X")
