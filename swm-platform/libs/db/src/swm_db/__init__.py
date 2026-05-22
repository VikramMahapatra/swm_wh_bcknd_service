from swm_db.base import AuditBase, AuditMixin, Base, SoftDeleteMixin, TimestampMixin
from swm_db.base_model import (
    AuditMixin as DomainAuditMixin,
    FleetBase,
    FleetBaseModel,
    NAMING_CONVENTION,
    SoftDeleteMixin as DomainSoftDeleteMixin,
    TimestampMixin as DomainTimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)
from swm_db.contractor_repository import ContractorRepository
from swm_db.device_vehicle_assignment_repository import DeviceVehicleAssignmentRepository
from swm_db.device_vehicle_assignment_service import AssignmentCreateInput, DeviceVehicleAssignmentService
from swm_db.device_repository import DeviceRepository
from swm_db.device_service import DeviceCreateInput, DeviceService, DeviceUpdateInput
from swm_db.engine import DatabaseSessionManager, EngineConfig, build_async_engine
from swm_db.geofence_repository import GeofenceRepository
from swm_db.models import (
    AlertActionORM,
    AlertORM,
    AuthPermissionORM,
    AuthRefreshTokenORM,
    AuthRoleORM,
    AuthUserORM,
    auth_role_permissions,
    auth_user_roles,
    AnalyticsDailyKPIORM,
    AnalyticsGeofenceEventORM,
    AnalyticsIdleRecordORM,
    AnalyticsOverspeedEventORM,
    AnalyticsTripRecordORM,
    AnalyticsVehicleStateORM,
    AuditLogORM,
    ContractorORM,
    DeviceEventORM,
    DeviceORM,
    DeviceVehicleAssignmentORM,
    GeofenceORM,
    OperationalCategoryORM,
    RouteORM,
    SystemConfigurationORM,
    VehicleORM,
    VendorORM,
    WardORM,
)
from swm_db.route_repository import RouteRepository
from swm_db.repository import Page, Repository
from swm_db.session import get_db_session, override_session_manager, session_manager
from swm_db.vendor_repository import VendorRepository
from swm_db.vendor_service import VendorCreateInput, VendorService, VendorUpdateInput
from swm_db.ward_repository import WardRepository
from swm_db.vehicle_repository import VehicleRepository
from swm_db.vehicle_service import VehicleCreateInput, VehicleService, VehicleUpdateInput

__all__ = [
    "AuditBase",
    "AuditMixin",
    "Base",
    "DatabaseSessionManager",
    "AnalyticsVehicleStateORM",
    "AnalyticsTripRecordORM",
    "AnalyticsIdleRecordORM",
    "AnalyticsOverspeedEventORM",
    "AnalyticsGeofenceEventORM",
    "AnalyticsDailyKPIORM",
    "AlertORM",
    "AlertActionORM",
    "AuthPermissionORM",
    "AuthRefreshTokenORM",
    "AuthRoleORM",
    "AuthUserORM",
    "auth_role_permissions",
    "auth_user_roles",
    "SystemConfigurationORM",
    "OperationalCategoryORM",
    "AuditLogORM",
    "DeviceEventORM",
    "DeviceORM",
    "DeviceVehicleAssignmentORM",
    "VehicleORM",
    "ContractorORM",
    "WardORM",
    "RouteORM",
    "GeofenceORM",
    "ContractorRepository",
    "WardRepository",
    "RouteRepository",
    "GeofenceRepository",
    "DeviceRepository",
    "DeviceService",
    "DeviceCreateInput",
    "DeviceUpdateInput",
    "DeviceVehicleAssignmentRepository",
    "DeviceVehicleAssignmentService",
    "AssignmentCreateInput",
    "VendorORM",
    "VendorRepository",
    "VendorService",
    "VendorCreateInput",
    "VendorUpdateInput",
    "VehicleRepository",
    "VehicleService",
    "VehicleCreateInput",
    "VehicleUpdateInput",
    "EngineConfig",
    "FleetBase",
    "FleetBaseModel",
    "NAMING_CONVENTION",
    "Page",
    "Repository",
    "UUIDPrimaryKeyMixin",
    "VersionMixin",
    "SoftDeleteMixin",
    "DomainSoftDeleteMixin",
    "TimestampMixin",
    "DomainTimestampMixin",
    "DomainAuditMixin",
    "build_async_engine",
    "get_db_session",
    "override_session_manager",
    "session_manager",
]

