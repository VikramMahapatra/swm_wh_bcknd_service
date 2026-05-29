import { Fragment, useState, useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import { PageHeader } from "@/components/PageHeader";
import { 
  Download, 
  FileText, 
  Truck, 
  MapPin, 
  Users, 
  Fuel, 
  AlertTriangle, 
  Scale,
  Calendar,
  Filter,
  FileSpreadsheet,
  Printer,
  TrendingUp,
  TrendingDown,
  Clock,
  Route,
  Trash2,
  Building,
  Shield,
  IdCard,
  Gauge,
  XCircle,
  WifiOff,
  Zap,
  ArrowRightLeft,
  Wrench,
  Mail,
  Send,
  CheckCircle2,
  ChevronRight
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { useTrucks, useDrivers, useReportsData, useZones, useWards, useVehicles } from "@/hooks/useDataQueries";
import { differenceInDays, parseISO, format } from "date-fns";
import { Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

// Reports data is loaded from the backend.

const ITEMS_PER_PAGE = 5;

const getDateValue = (value: unknown): string | undefined =>
  typeof value === "string" && value.trim() ? value : undefined;

const safeParseISO = (value?: string) => (value ? parseISO(value) : null);

const getTruckInsuranceDate = (truck: any) =>
  getDateValue(truck.insuranceExpiry ?? truck.insurance_expiry);

const getTruckFitnessDate = (truck: any) =>
  getDateValue(truck.fitnessExpiry ?? truck.fitness_expiry);

const getDriverLicenseDate = (driver: any) =>
  getDateValue(driver.licenseExpiry ?? driver.license_expiry);

export default function Reports() {
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get("tab") || "daily";
  const { toast } = useToast();
  
  // API Hooks
  const { data: trucksData = [] } = useTrucks();
  const { data: driversData = [] } = useDrivers();
  const { data: zonesData = [] } = useZones();
  const { data: wardsData = [] } = useWards();
  const { data: vehiclesData = [] } = useVehicles();
  
  // State for API data
  const [trucks, setTrucks] = useState<any[]>([]);
  const [drivers, setDrivers] = useState<any[]>([]);
  
  // Sync API data to state
  useEffect(() => {
    setTrucks(trucksData);
  }, [trucksData]);
  
  useEffect(() => {
    setDrivers(driversData);
  }, [driversData]);
  
  const today = format(new Date(), "yyyy-MM-dd");
  const [activeTab, setActiveTab] = useState(initialTab);
  const [dateFrom, setDateFrom] = useState(today);
  const [dateTo, setDateTo] = useState(today);
  const [selectedZone, setSelectedZone] = useState("all");
  const [selectedWard, setSelectedWard] = useState("all");
  const [selectedTruck, setSelectedTruck] = useState("all");
  const [appliedFilters, setAppliedFilters] = useState({
    dateFrom: today,
    dateTo: today,
    selectedZone: "all",
    selectedWard: "all",
    selectedTruck: "all",
  });
  const wardOptions = useMemo(() => {
    if (selectedZone === "all") return wardsData;
    return wardsData.filter((ward: any) => String(ward.zoneId ?? ward.zone_id ?? "") === selectedZone);
  }, [selectedZone, wardsData]);
  const truckOptions = useMemo(() => {
    const zoneByWardId = new Map(
      wardsData.map((ward: any) => [String(ward.id), String(ward.zoneId ?? ward.zone_id ?? "")])
    );
    return vehiclesData.filter((truck: any) => {
      const wardId = String(truck.ward_id ?? truck.wardId ?? "");
      const zoneId = String(truck.zone_id ?? truck.zoneId ?? zoneByWardId.get(wardId) ?? "");
      if (selectedZone !== "all" && zoneId !== selectedZone) return false;
      if (selectedWard !== "all" && wardId !== selectedWard) return false;
      return true;
    });
  }, [selectedZone, selectedWard, vehiclesData, wardsData]);
  const { data: reportsData = {}, isLoading: isLoadingReports } = useReportsData({
    date_from: appliedFilters.dateFrom,
    date_to: appliedFilters.dateTo,
    zone_id: appliedFilters.selectedZone === "all" ? undefined : appliedFilters.selectedZone,
    ward_id: appliedFilters.selectedWard === "all" ? undefined : appliedFilters.selectedWard,
    vehicle_id: appliedFilters.selectedTruck === "all" ? undefined : appliedFilters.selectedTruck,
  });

  const dailyPickupCoverageData: any[] = (reportsData as any).daily_pickup_coverage || [];
  const routePerformanceData: any[] = (reportsData as any).route_performance || [];
  const truckUtilizationData: any[] = (reportsData as any).truck_utilization || [];
  const tripCompletedData: any[] = (reportsData as any).trip_completed || [];
  const fuelConsumptionData: any[] = (reportsData as any).fuel_consumption || [];
  const driverAttendanceData: any[] = (reportsData as any).driver_attendance || [];
  const complaintsData: any[] = (reportsData as any).complaints || [];
  const dumpYardData: any[] = (reportsData as any).dump_yard || [];
  const zoneWiseData: any[] = (reportsData as any).zone_wise || [];
  const lateArrivalData: any[] = (reportsData as any).late_arrival || [];
  const driverBehaviorData: any[] = (reportsData as any).driver_behavior || [];
  const vehicleStatusData: any[] = (reportsData as any).vehicle_status || [];
  const spareUsageData: any[] = (reportsData as any).spare_usage || [];
  const dailyTotalPoints = dailyPickupCoverageData.reduce((sum, row) => sum + (Number(row.totalPoints) || 0), 0);
  const dailyCoveredPoints = dailyPickupCoverageData.reduce((sum, row) => sum + (Number(row.covered) || 0), 0);
  const dailyMissedPoints = Math.max(dailyTotalPoints - dailyCoveredPoints, 0);
  const dailyCompletionPct = dailyTotalPoints > 0 ? (dailyCoveredPoints / dailyTotalPoints) * 100 : 0;
  const tripTotalCompleted = tripCompletedData.length;
  const tripTotalPickupPoints = tripCompletedData.reduce((sum, row) => sum + (Number(row.pickups) || 0), 0);
  const tripTotalMinutes = tripCompletedData.reduce((sum, row) => sum + (Number(row.durationMinutes) || 0), 0);
  const tripAvgMinutes = tripTotalCompleted > 0 ? Math.round(tripTotalMinutes / tripTotalCompleted) : 0;
  
  // Email export dialog state
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);
  const [emailAddress, setEmailAddress] = useState("");
  const [emailReportType, setEmailReportType] = useState("");
  const [sendingEmail, setSendingEmail] = useState(false);
  
  // Pagination states for each report
  const [dailyPage, setDailyPage] = useState(1);
  const [expandedDailyRows, setExpandedDailyRows] = useState<Record<string, boolean>>({});
  const [routePage, setRoutePage] = useState(1);
  const [truckPage, setTruckPage] = useState(1);
  const [tripPage, setTripPage] = useState(1);
  const [expandedTripRows, setExpandedTripRows] = useState<Record<string, boolean>>({});
  const [fuelPage, setFuelPage] = useState(1);
  const [driverPage, setDriverPage] = useState(1);
  const [lateArrivalPage, setLateArrivalPage] = useState(1);
  const [behaviorPage, setBehaviorPage] = useState(1);
  const [vehicleStatusPage, setVehicleStatusPage] = useState(1);
  const [spareUsagePage, setSpareUsagePage] = useState(1);
  const [complaintsPage, setComplaintsPage] = useState(1);
  const [dumpYardPage, setDumpYardPage] = useState(1);
  const [expiryTruckPage, setExpiryTruckPage] = useState(1);
  const [expiryDriverPage, setExpiryDriverPage] = useState(1);

  useEffect(() => {
    if (selectedZone !== "all" && selectedWard !== "all") {
      const wardBelongsToZone = wardOptions.some((ward: any) => String(ward.id) === selectedWard);
      if (!wardBelongsToZone) {
        setSelectedWard("all");
      }
    }
  }, [selectedZone, selectedWard, wardOptions]);

  useEffect(() => {
    if (selectedTruck === "all") return;
    const truckStillVisible = truckOptions.some((truck: any) => String(truck.id) === selectedTruck);
    if (!truckStillVisible) {
      setSelectedTruck("all");
    }
  }, [selectedTruck, truckOptions]);

  const handleApplyFilters = () => {
    setAppliedFilters({
      dateFrom,
      dateTo,
      selectedZone,
      selectedWard,
      selectedTruck,
    });
    setDailyPage(1);
    setTripPage(1);
    setExpandedDailyRows({});
    setExpandedTripRows({});
  };

  const toggleDailyRow = (rowId: string) => {
    setExpandedDailyRows((current) => ({
      ...current,
      [rowId]: !current[rowId],
    }));
  };

  const toggleTripRow = (rowId: string) => {
    setExpandedTripRows((current) => ({
      ...current,
      [rowId]: !current[rowId],
    }));
  };

  // Filter states for each report
  const [dailyStatusFilter, setDailyStatusFilter] = useState("all");
  const [routeEfficiencyFilter, setRouteEfficiencyFilter] = useState("all");
  const [truckTypeFilter, setTruckTypeFilter] = useState("all");
  const [fuelAnomalyFilter, setFuelAnomalyFilter] = useState("all");
  const [driverOnTimeFilter, setDriverOnTimeFilter] = useState("all");
  const [lateStatusFilter, setLateStatusFilter] = useState("all");
  const [behaviorTypeFilter, setBehaviorTypeFilter] = useState("all");
  const [behaviorSeverityFilter, setBehaviorSeverityFilter] = useState("all");
  const [vehicleStatusFilter, setVehicleStatusFilter] = useState("all");
  const [spareStatusFilter, setSpareStatusFilter] = useState("all");
  const [complaintsStatusFilter, setComplaintsStatusFilter] = useState("all");
  const [complaintsTypeFilter, setComplaintsTypeFilter] = useState("all");
  const [expiryStatusFilter, setExpiryStatusFilter] = useState("all");
  const [dumpYardSiteFilter, setDumpYardSiteFilter] = useState("all");
  const [lateZoneFilter, setLateZoneFilter] = useState("all");
  const [lateWardFilter, setLateWardFilter] = useState("all");
  const [lateVendorFilter, setLateVendorFilter] = useState("all");
  const [lateRouteTypeFilter, setLateRouteTypeFilter] = useState("all");
  
  // Sync with URL param
  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  // Pagination helper
  const paginate = <T,>(data: T[], page: number): T[] => {
    const start = (page - 1) * ITEMS_PER_PAGE;
    return data.slice(start, start + ITEMS_PER_PAGE);
  };

  const getTotalPages = (totalItems: number): number => {
    return Math.ceil(totalItems / ITEMS_PER_PAGE);
  };

  const renderPagination = (currentPage: number, totalItems: number, setPage: (page: number) => void) => {
    const totalPages = getTotalPages(totalItems);
    if (totalPages <= 1) return null;

    const handlePageChange = (e: React.MouseEvent, newPage: number) => {
      e.preventDefault();
      e.stopPropagation();
      setPage(newPage);
    };

    return (
      <div className="flex flex-col items-center gap-3 mt-4 pt-4 border-t">
        <Pagination>
          <PaginationContent className="gap-1">
            <PaginationItem>
              <PaginationPrevious 
                onClick={(e) => handlePageChange(e, Math.max(1, currentPage - 1))}
                className={`h-8 text-xs px-2 ${currentPage === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}`}
              />
            </PaginationItem>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum: number;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }
              return (
                <PaginationItem key={pageNum}>
                  <PaginationLink
                    onClick={(e) => handlePageChange(e, pageNum)}
                    isActive={currentPage === pageNum}
                    className="h-8 w-8 text-xs cursor-pointer"
                  >
                    {pageNum}
                  </PaginationLink>
                </PaginationItem>
              );
            })}
            <PaginationItem>
              <PaginationNext 
                onClick={(e) => handlePageChange(e, Math.min(totalPages, currentPage + 1))}
                className={`h-8 text-xs px-2 ${currentPage === totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}`}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
        <span className="text-xs text-muted-foreground whitespace-nowrap">
          Showing {Math.min((currentPage - 1) * ITEMS_PER_PAGE + 1, totalItems)}-{Math.min(currentPage * ITEMS_PER_PAGE, totalItems)} of {totalItems} items
        </span>
      </div>
    );
  };

  type ExportColumn = {
    key: string;
    label: string;
    width?: number;
    align?: "Left" | "Center" | "Right";
  };

  type ExportSection = {
    title: string;
    columns: ExportColumn[];
    rows: any[];
    childKey?: string;
    childTitle?: string;
    childColumns?: ExportColumn[];
  };

  const excelEscape = (value: unknown) =>
    String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  const getValue = (row: any, key: string) =>
    key.split(".").reduce((current, part) => (current == null ? undefined : current[part]), row);

  const normalizeSheetName = (value: string) =>
    value.replace(/[\\/?*[\]:]/g, " ").replace(/\s+/g, " ").trim().slice(0, 31) || "Report";

  const isNumericExcelValue = (value: unknown) =>
    typeof value === "number" || (typeof value === "string" && value.trim() !== "" && !Number.isNaN(Number(value)) && !/^0\d+/.test(value.trim()));

  const excelCell = (value: unknown, style = "Cell", mergeAcross = 0, align?: ExportColumn["align"]) => {
    const actualValue = value ?? "-";
    const isNumber = isNumericExcelValue(actualValue);
    const styleId = align === "Center" ? `${style}Center` : align === "Right" ? `${style}Right` : style;
    return `<Cell ss:StyleID="${styleId}"${mergeAcross ? ` ss:MergeAcross="${mergeAcross}"` : ""}><Data ss:Type="${isNumber ? "Number" : "String"}">${excelEscape(actualValue)}</Data></Cell>`;
  };

  const excelRow = (cells: string[], height?: number) =>
    `<Row${height ? ` ss:Height="${height}"` : ""}>${cells.join("")}</Row>`;

  const excelColumnsXml = (sections: ExportSection[]) => {
    const maxColumns = Math.max(
      1,
      ...sections.map((section) => Math.max(section.columns.length, section.childColumns?.length || 0))
    );
    const widths = Array.from({ length: maxColumns }, (_, index) => {
      const width = Math.max(
        70,
        ...sections.flatMap((section) => [
          section.columns[index]?.width || 0,
          section.childColumns?.[index]?.width || 0,
        ])
      );
      return `<Column ss:Width="${width}"/>`;
    });
    return widths.join("");
  };

  const buildExcelWorkbook = (reportTitle: string, sections: ExportSection[]) => {
    const generatedAt = format(new Date(), "yyyy-MM-dd HH:mm:ss");
    const filterText = `Filters: ${appliedFilters.dateFrom} to ${appliedFilters.dateTo}, Zone ${appliedFilters.selectedZone}, Ward ${appliedFilters.selectedWard}, Truck ${appliedFilters.selectedTruck}`;
    const maxColumns = Math.max(
      1,
      ...sections.map((section) => Math.max(section.columns.length, section.childColumns?.length || 0))
    );
    const rows: string[] = [
      excelRow([excelCell(reportTitle, "Title", Math.max(maxColumns - 1, 0))], 28),
      excelRow([excelCell(filterText, "Meta", Math.max(maxColumns - 1, 0))]),
      excelRow([excelCell(`Generated: ${generatedAt}`, "Meta", Math.max(maxColumns - 1, 0))]),
      excelRow(Array.from({ length: maxColumns }, () => excelCell("", "Blank"))),
    ];

    sections.forEach((section) => {
      rows.push(excelRow([excelCell(section.title, "Section", Math.max(maxColumns - 1, 0))], 22));
      rows.push(excelRow(section.columns.map((column) => excelCell(column.label, "Header", 0, column.align))));

      if (section.rows.length === 0) {
        rows.push(excelRow([excelCell("No records found for selected filters.", "Muted", Math.max(section.columns.length - 1, 0))]));
      }

      section.rows.forEach((row) => {
        const rowStyle = row.isLate || row.status === "late" ? "LateCell" : "Cell";
        rows.push(
          excelRow(
            section.columns.map((column) => excelCell(getValue(row, column.key), rowStyle, 0, column.align))
          )
        );

        const childRows = section.childKey ? getValue(row, section.childKey) : undefined;
        if (Array.isArray(childRows) && childRows.length > 0 && section.childColumns?.length) {
          rows.push(
            excelRow([
              excelCell(
                `${section.childTitle || "Details"} - ${row.truck || row.route || row.date || row.id || ""}`,
                "SubSection",
                Math.max(section.childColumns.length - 1, 0)
              ),
            ])
          );
          rows.push(excelRow(section.childColumns.map((column) => excelCell(column.label, "SubHeader", 0, column.align))));
          childRows.forEach((child) => {
            const childStyle = child.status === "missed" ? "MissedCell" : child.isGtcPoint ? "GtcCell" : "ChildCell";
            rows.push(
              excelRow(section.childColumns!.map((column) => excelCell(getValue(child, column.key), childStyle, 0, column.align)))
            );
          });
          rows.push(excelRow(Array.from({ length: section.childColumns.length }, () => excelCell("", "Blank"))));
        }
      });

      rows.push(excelRow(Array.from({ length: maxColumns }, () => excelCell("", "Blank"))));
    });

    return `<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:html="http://www.w3.org/TR/REC-html40">
 <Styles>
  <Style ss:ID="Default" ss:Name="Normal"><Alignment ss:Vertical="Center"/><Font ss:FontName="Calibri" ss:Size="11"/></Style>
  <Style ss:ID="Title"><Alignment ss:Horizontal="Center" ss:Vertical="Center"/><Font ss:FontName="Calibri" ss:Size="16" ss:Bold="1" ss:Color="#FFFFFF"/><Interior ss:Color="#1F4E78" ss:Pattern="Solid"/></Style>
  <Style ss:ID="Meta"><Font ss:Color="#666666"/><Interior ss:Color="#F3F6FA" ss:Pattern="Solid"/></Style>
  <Style ss:ID="Section"><Font ss:Bold="1" ss:Size="13" ss:Color="#FFFFFF"/><Interior ss:Color="#305496" ss:Pattern="Solid"/></Style>
  <Style ss:ID="SubSection"><Font ss:Bold="1" ss:Color="#1F4E78"/><Interior ss:Color="#D9EAF7" ss:Pattern="Solid"/></Style>
  <Style ss:ID="Header"><Alignment ss:Horizontal="Center"/><Font ss:Bold="1" ss:Color="#FFFFFF"/><Interior ss:Color="#4472C4" ss:Pattern="Solid"/><Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1"/></Borders></Style>
  <Style ss:ID="HeaderCenter" ss:Parent="Header"><Alignment ss:Horizontal="Center"/></Style>
  <Style ss:ID="HeaderRight" ss:Parent="Header"><Alignment ss:Horizontal="Right"/></Style>
  <Style ss:ID="SubHeader"><Alignment ss:Horizontal="Center"/><Font ss:Bold="1" ss:Color="#1F4E78"/><Interior ss:Color="#BFD7EA" ss:Pattern="Solid"/></Style>
  <Style ss:ID="SubHeaderCenter" ss:Parent="SubHeader"><Alignment ss:Horizontal="Center"/></Style>
  <Style ss:ID="SubHeaderRight" ss:Parent="SubHeader"><Alignment ss:Horizontal="Right"/></Style>
  <Style ss:ID="Cell"><Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/><Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E5E7EB"/></Borders></Style>
  <Style ss:ID="CellCenter" ss:Parent="Cell"><Alignment ss:Horizontal="Center"/></Style>
  <Style ss:ID="CellRight" ss:Parent="Cell"><Alignment ss:Horizontal="Right"/></Style>
  <Style ss:ID="ChildCell" ss:Parent="Cell"><Interior ss:Color="#F8FBFD" ss:Pattern="Solid"/></Style>
  <Style ss:ID="ChildCellCenter" ss:Parent="ChildCell"><Alignment ss:Horizontal="Center"/></Style>
  <Style ss:ID="ChildCellRight" ss:Parent="ChildCell"><Alignment ss:Horizontal="Right"/></Style>
  <Style ss:ID="LateCell" ss:Parent="Cell"><Font ss:Color="#B91C1C" ss:Bold="1"/><Interior ss:Color="#FEE2E2" ss:Pattern="Solid"/></Style>
  <Style ss:ID="LateCellCenter" ss:Parent="LateCell"><Alignment ss:Horizontal="Center"/></Style>
  <Style ss:ID="LateCellRight" ss:Parent="LateCell"><Alignment ss:Horizontal="Right"/></Style>
  <Style ss:ID="MissedCell" ss:Parent="ChildCell"><Font ss:Color="#B91C1C"/><Interior ss:Color="#FFF1F2" ss:Pattern="Solid"/></Style>
  <Style ss:ID="MissedCellCenter" ss:Parent="MissedCell"><Alignment ss:Horizontal="Center"/></Style>
  <Style ss:ID="MissedCellRight" ss:Parent="MissedCell"><Alignment ss:Horizontal="Right"/></Style>
  <Style ss:ID="GtcCell" ss:Parent="ChildCell"><Font ss:Color="#1D4ED8" ss:Bold="1"/><Interior ss:Color="#DBEAFE" ss:Pattern="Solid"/></Style>
  <Style ss:ID="GtcCellCenter" ss:Parent="GtcCell"><Alignment ss:Horizontal="Center"/></Style>
  <Style ss:ID="GtcCellRight" ss:Parent="GtcCell"><Alignment ss:Horizontal="Right"/></Style>
  <Style ss:ID="Muted"><Font ss:Color="#6B7280" ss:Italic="1"/></Style>
  <Style ss:ID="Blank"><Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/></Style>
 </Styles>
 <Worksheet ss:Name="${excelEscape(normalizeSheetName(reportTitle))}">
  <Table>${excelColumnsXml(sections)}${rows.join("")}</Table>
  <WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel"><FreezePanes/><FrozenNoSplit/><SplitHorizontal>5</SplitHorizontal><TopRowBottomPane>5</TopRowBottomPane><ProtectObjects>False</ProtectObjects><ProtectScenarios>False</ProtectScenarios></WorksheetOptions>
 </Worksheet>
</Workbook>`;
  };

  const downloadExcelWorkbook = (reportTitle: string, sections: ExportSection[]) => {
    const workbookXml = buildExcelWorkbook(reportTitle, sections);
    const blob = new Blob([workbookXml], { type: "application/vnd.ms-excel;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${reportTitle.replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "").toLowerCase()}_${format(new Date(), "yyyyMMdd_HHmmss")}.xls`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const makeSectionsForReport = (reportType: string): { title: string; sections: ExportSection[] } => {
    const commonColumns: Record<string, ExportColumn[]> = {
      daily_collection: [
        { key: "date", label: "Date", width: 95 },
        { key: "ward", label: "Ward", width: 130 },
        { key: "zone", label: "Zone", width: 130 },
        { key: "truck", label: "Truck", width: 130 },
        { key: "driver", label: "Driver", width: 120 },
        { key: "route", label: "Route", width: 140 },
        { key: "totalPoints", label: "Total Points", width: 90, align: "Center" },
        { key: "covered", label: "Covered", width: 80, align: "Center" },
        { key: "missed", label: "Missed", width: 80, align: "Center" },
        { key: "status", label: "Status", width: 100, align: "Center" },
      ],
      pickup_details: [
        { key: "sequenceNo", label: "Seq", width: 55, align: "Center" },
        { key: "pickupName", label: "Pickup Point", width: 260 },
        { key: "expectedTime", label: "Expected", width: 90, align: "Center" },
        { key: "actualTime", label: "First Crossed", width: 100, align: "Center" },
        { key: "lastCrossedTime", label: "Last Crossed", width: 100, align: "Center" },
        { key: "crossingCount", label: "Count", width: 70, align: "Center" },
        { key: "nearestDistanceM", label: "Nearest (m)", width: 90, align: "Right" },
        { key: "status", label: "Status", width: 90, align: "Center" },
      ],
      trips_completed: [
        { key: "date", label: "Date", width: 95 },
        { key: "truck", label: "Truck", width: 130 },
        { key: "route", label: "Route", width: 140 },
        { key: "zone", label: "Zone", width: 120 },
        { key: "ward", label: "Ward", width: 120 },
        { key: "startTime", label: "Start", width: 80, align: "Center" },
        { key: "endTime", label: "GTC Entry", width: 90, align: "Center" },
        { key: "duration", label: "Duration", width: 90, align: "Center" },
        { key: "gtcPoint", label: "GTC Point", width: 230 },
        { key: "status", label: "Status", width: 90, align: "Center" },
      ],
      late_arrival: [
        { key: "date", label: "Date", width: 95 },
        { key: "zone", label: "Zone", width: 120 },
        { key: "truck", label: "Truck", width: 130 },
        { key: "route", label: "Route", width: 130 },
        { key: "firstPickupPoint", label: "First Pickup", width: 240 },
        { key: "scheduledTime", label: "Expected", width: 90, align: "Center" },
        { key: "allowedUntil", label: "Allowed Until", width: 100, align: "Center" },
        { key: "actualTime", label: "Actual Entry", width: 100, align: "Center" },
        { key: "lateByMinutes", label: "Late By (min)", width: 95, align: "Center" },
        { key: "status", label: "Status", width: 90, align: "Center" },
      ],
    };

    const simpleReport = (title: string, rows: any[], columns: ExportColumn[]): { title: string; sections: ExportSection[] } => ({
      title,
      sections: [{ title, rows, columns }],
    });

    switch (reportType) {
      case "daily_collection":
        return {
          title: "Daily Pickup Coverage Report",
          sections: [{
            title: "Daily Pickup Coverage",
            rows: dailyStatusFilter === "all" ? dailyPickupCoverageData : dailyPickupCoverageData.filter(row => row.status === dailyStatusFilter),
            columns: commonColumns.daily_collection,
            childKey: "pickupDetails",
            childTitle: "Pickup Point Details",
            childColumns: commonColumns.pickup_details,
          }],
        };
      case "trips_completed":
        return {
          title: "Trips Completed Report",
          sections: [{
            title: "Completed Trips",
            rows: tripCompletedData,
            columns: commonColumns.trips_completed,
            childKey: "tripDetails",
            childTitle: "Trip Pickup Details",
            childColumns: commonColumns.pickup_details,
          }],
        };
      case "late_arrival":
        return simpleReport(
          "First Pickup Entry Report",
          lateArrivalData.filter(row => lateStatusFilter === "all" ? true : lateStatusFilter === "late" ? row.isLate : !row.isLate),
          commonColumns.late_arrival
        );
      case "route_performance":
        return simpleReport("Route Performance Report", routePerformanceData, [
          { key: "route", label: "Route", width: 160 },
          { key: "zone", label: "Zone", width: 120 },
          { key: "ward", label: "Ward", width: 120 },
          { key: "assignedTrucks", label: "Assigned Trucks", width: 110, align: "Center" },
          { key: "completedTrips", label: "Completed Trips", width: 110, align: "Center" },
          { key: "avgTime", label: "Average Time", width: 110, align: "Center" },
          { key: "efficiency", label: "Efficiency %", width: 100, align: "Center" },
        ]);
      case "truck_utilization":
        return simpleReport("Truck Utilization Report", truckUtilizationData, [
          { key: "truck", label: "Truck", width: 130 },
          { key: "type", label: "Type", width: 120 },
          { key: "trips", label: "Trips", width: 80, align: "Center" },
          { key: "operatingHours", label: "Operating Hours", width: 120, align: "Right" },
          { key: "idleTime", label: "Idle Time", width: 100, align: "Right" },
          { key: "distance", label: "Distance", width: 100, align: "Right" },
          { key: "utilization", label: "Utilization %", width: 110, align: "Center" },
        ]);
      case "fuel_consumption":
        return simpleReport("Fuel Consumption Report", fuelConsumptionData, [
          { key: "date", label: "Date", width: 95 },
          { key: "truck", label: "Truck", width: 130 },
          { key: "fuel", label: "Fuel", width: 90, align: "Right" },
          { key: "distance", label: "Distance", width: 100, align: "Right" },
          { key: "efficiency", label: "Efficiency", width: 100, align: "Right" },
          { key: "cost", label: "Cost", width: 100, align: "Right" },
          { key: "anomaly", label: "Anomaly", width: 100, align: "Center" },
        ]);
      case "driver_attendance":
        return simpleReport("Driver Attendance Report", driverAttendanceData, [
          { key: "date", label: "Date", width: 95 },
          { key: "driver", label: "Driver", width: 150 },
          { key: "truck", label: "Truck", width: 130 },
          { key: "shift", label: "Shift", width: 100 },
          { key: "checkIn", label: "Check In", width: 90, align: "Center" },
          { key: "checkOut", label: "Check Out", width: 90, align: "Center" },
          { key: "hours", label: "Hours", width: 80, align: "Right" },
          { key: "status", label: "Status", width: 100, align: "Center" },
        ]);
      case "driver_behavior":
        return simpleReport("Driver Behavior Report", driverBehaviorData, [
          { key: "date", label: "Date", width: 95 },
          { key: "driver", label: "Driver", width: 150 },
          { key: "truck", label: "Truck", width: 130 },
          { key: "type", label: "Type", width: 150 },
          { key: "location", label: "Location", width: 180 },
          { key: "time", label: "Time", width: 80, align: "Center" },
          { key: "severity", label: "Severity", width: 90, align: "Center" },
          { key: "action", label: "Action", width: 150 },
        ]);
      case "vehicle_status":
        return simpleReport("Vehicle Status Report", vehicleStatusData, [
          { key: "truck", label: "Truck", width: 130 },
          { key: "status", label: "Status", width: 100, align: "Center" },
          { key: "lastSeen", label: "Last Seen", width: 130 },
          { key: "location", label: "Location", width: 180 },
          { key: "battery", label: "Battery", width: 90, align: "Center" },
          { key: "signal", label: "Signal", width: 90, align: "Center" },
        ]);
      case "complaints":
        return simpleReport("Complaints Report", complaintsData, [
          { key: "id", label: "Complaint ID", width: 120 },
          { key: "date", label: "Date", width: 95 },
          { key: "type", label: "Type", width: 150 },
          { key: "location", label: "Location", width: 180 },
          { key: "status", label: "Status", width: 110, align: "Center" },
          { key: "assignedTo", label: "Assigned To", width: 150 },
          { key: "resolutionTime", label: "Resolution Time", width: 120 },
        ]);
      case "dumpyard_log":
        return simpleReport("Dump Yard Log Report", dumpYardData, [
          { key: "date", label: "Date", width: 95 },
          { key: "truck", label: "Truck", width: 130 },
          { key: "site", label: "Site", width: 180 },
          { key: "entryTime", label: "Entry Time", width: 90, align: "Center" },
          { key: "exitTime", label: "Exit Time", width: 90, align: "Center" },
          { key: "weight", label: "Weight", width: 90, align: "Right" },
          { key: "capacity", label: "Capacity %", width: 100, align: "Center" },
        ]);
      case "spare_usage":
        return simpleReport("Spare Vehicle Usage Report", spareUsageData, [
          { key: "date", label: "Date", width: 95 },
          { key: "spareTruck", label: "Spare Truck", width: 130 },
          { key: "originalTruck", label: "Original Truck", width: 130 },
          { key: "reason", label: "Reason", width: 180 },
          { key: "duration", label: "Duration", width: 100 },
          { key: "status", label: "Status", width: 100, align: "Center" },
        ]);
      case "expiry_report":
        return {
          title: "Expiry Report",
          sections: [
            {
              title: "Truck Expiry",
              rows: trucks,
              columns: [
                { key: "vehicle_number", label: "Truck", width: 130 },
                { key: "registration_number", label: "Registration", width: 140 },
                { key: "insuranceExpiry", label: "Insurance Expiry", width: 130 },
                { key: "fitnessExpiry", label: "Fitness Expiry", width: 130 },
                { key: "status", label: "Status", width: 100, align: "Center" },
              ],
            },
            {
              title: "Driver License Expiry",
              rows: drivers,
              columns: [
                { key: "name", label: "Driver", width: 150 },
                { key: "license_number", label: "License No.", width: 140 },
                { key: "licenseExpiry", label: "License Expiry", width: 130 },
                { key: "phone", label: "Phone", width: 120 },
                { key: "status", label: "Status", width: 100, align: "Center" },
              ],
            },
          ],
        };
      default:
        return simpleReport(reportType.replace(/_/g, " "), [], [{ key: "message", label: "Message", width: 240 }]);
    }
  };

  const handleDownload = (reportType: string, format: string) => {
    if (format === "excel") {
      const exportConfig = makeSectionsForReport(reportType);
      downloadExcelWorkbook(exportConfig.title, exportConfig.sections);
      toast({
        title: "Excel Download Started",
        description: `${exportConfig.title} has been exported with formatted grids and subgrids.`,
      });
      return;
    }

    toast({
      title: "Download Started",
      description: `Downloading ${reportType.replace(/_/g, ' ')} report as ${format.toUpperCase()} (with current filters applied)`,
    });
  };

  const handlePrint = (reportType: string) => {
    window.print();
  };
  
  const handleEmailExport = (reportType: string) => {
    setEmailReportType(reportType);
    setEmailDialogOpen(true);
  };
  
  const sendEmailReport = async () => {
    if (!emailAddress || !emailAddress.includes('@')) {
      toast({
        title: "Invalid Email",
        description: "Please enter a valid email address",
        variant: "destructive",
      });
      return;
    }
    
    setSendingEmail(true);
    // Simulate sending email
    await new Promise(resolve => setTimeout(resolve, 1500));
    setSendingEmail(false);
    setEmailDialogOpen(false);
    setEmailAddress("");
    
    toast({
      title: "Email Sent Successfully",
      description: `${emailReportType.replace(/_/g, ' ')} report has been sent to ${emailAddress} with current filters applied`,
    });
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Email Export Dialog */}
      <Dialog open={emailDialogOpen} onOpenChange={setEmailDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              Email Report
            </DialogTitle>
            <DialogDescription>
              Send the {emailReportType.replace(/_/g, ' ')} report with current filters to an email address.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Email Address</label>
              <Input
                type="email"
                placeholder="Enter email address"
                value={emailAddress}
                onChange={(e) => setEmailAddress(e.target.value)}
              />
            </div>
            <div className="text-sm text-muted-foreground">
              <p>Report will include:</p>
              <ul className="list-disc list-inside mt-1 space-y-1">
                <li>Current filter selections applied</li>
                <li>Date range: {dateFrom} to {dateTo}</li>
                <li>Format: PDF attachment</li>
              </ul>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEmailDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={sendEmailReport} disabled={sendingEmail}>
              {sendingEmail ? (
                <>Sending...</>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Send Email
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Header */}
      <PageHeader
        category="Analytics"
        title="Reports Center"
        description="Generate, filter and download comprehensive fleet reports"
        icon={FileText}
        badge={{
          label: "13 Report Types",
          variant: "outline",
          className: "bg-primary/10 text-primary border-primary/20",
        }}
      />

      {/* Global Filters */}
      <Card className="border-primary/20 bg-gradient-to-r from-primary/5 to-transparent">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">Report Filters</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">From Date</label>
              <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">To Date</label>
              <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Zone</label>
              <Select value={selectedZone} onValueChange={setSelectedZone}>
                <SelectTrigger>
                  <SelectValue placeholder="All Zones" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Zones</SelectItem>
                  {zonesData.map((zone: any) => (
                    <SelectItem key={String(zone.id)} value={String(zone.id)}>
                      {zone.name || zone.zone_name || zone.code || zone.zone_code || zone.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Ward</label>
              <Select value={selectedWard} onValueChange={setSelectedWard}>
                <SelectTrigger>
                  <SelectValue placeholder="All Wards" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Wards</SelectItem>
                  {wardOptions.map((ward: any) => (
                    <SelectItem key={String(ward.id)} value={String(ward.id)}>
                      {ward.name || ward.ward_name || ward.code || ward.ward_code || ward.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Truck</label>
              <Select value={selectedTruck} onValueChange={setSelectedTruck}>
                <SelectTrigger>
                  <SelectValue placeholder="All Trucks" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Trucks</SelectItem>
                  {truckOptions.map((truck: any) => (
                    <SelectItem key={String(truck.id)} value={String(truck.id)}>
                      {truck.vehicle_number || truck.vehicleNumber || truck.registration_number || truck.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium opacity-0">Apply</label>
              <Button className="w-full" onClick={handleApplyFilters} disabled={isLoadingReports}>
                <Filter className="h-4 w-4 mr-2" />
                Apply
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Report Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid grid-cols-4 md:grid-cols-12 h-auto gap-1 bg-muted/50 p-1">
          <TabsTrigger value="daily" className="flex items-center gap-1 text-xs md:text-sm">
            <MapPin className="h-3 w-3 md:h-4 md:w-4" />
            <span className="hidden md:inline">Pickup</span> Coverage
          </TabsTrigger>
          <TabsTrigger value="route" className="flex items-center gap-1 text-xs md:text-sm">
            <Route className="h-3 w-3 md:h-4 md:w-4" />
            Route
          </TabsTrigger>
          <TabsTrigger value="truck" className="flex items-center gap-1 text-xs md:text-sm">
            <Truck className="h-3 w-3 md:h-4 md:w-4" />
            Truck
          </TabsTrigger>
          <TabsTrigger value="trips-completed" className="flex items-center gap-1 text-xs md:text-sm">
            <CheckCircle2 className="h-3 w-3 md:h-4 md:w-4" />
            Trips
          </TabsTrigger>
          <TabsTrigger value="fuel" className="flex items-center gap-1 text-xs md:text-sm">
            <Fuel className="h-3 w-3 md:h-4 md:w-4" />
            Fuel
          </TabsTrigger>
          <TabsTrigger value="driver" className="flex items-center gap-1 text-xs md:text-sm">
            <Users className="h-3 w-3 md:h-4 md:w-4" />
            Driver
          </TabsTrigger>
          <TabsTrigger value="late-arrival" className="flex items-center gap-1 text-xs md:text-sm">
            <Clock className="h-3 w-3 md:h-4 md:w-4" />
            First Pickup
          </TabsTrigger>
          <TabsTrigger value="behavior" className="flex items-center gap-1 text-xs md:text-sm">
            <Gauge className="h-3 w-3 md:h-4 md:w-4" />
            Behavior
          </TabsTrigger>
          <TabsTrigger value="vehicle-status" className="flex items-center gap-1 text-xs md:text-sm">
            <WifiOff className="h-3 w-3 md:h-4 md:w-4" />
            Vehicle Status
          </TabsTrigger>
          <TabsTrigger value="spare-usage" className="flex items-center gap-1 text-xs md:text-sm">
            <ArrowRightLeft className="h-3 w-3 md:h-4 md:w-4" />
            Spare Usage
          </TabsTrigger>
          <TabsTrigger value="complaints" className="flex items-center gap-1 text-xs md:text-sm">
            <AlertTriangle className="h-3 w-3 md:h-4 md:w-4" />
            Complaints
          </TabsTrigger>
          <TabsTrigger value="dumpyard" className="flex items-center gap-1 text-xs md:text-sm">
            <Building className="h-3 w-3 md:h-4 md:w-4" />
            Dump Yard
          </TabsTrigger>
          <TabsTrigger value="expiry" className="flex items-center gap-1 text-xs md:text-sm">
            <Shield className="h-3 w-3 md:h-4 md:w-4" />
            Expiry
          </TabsTrigger>
        </TabsList>

        {/* Daily Collection Report */}
        <TabsContent value="daily" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <MapPin className="h-5 w-5 text-primary" />
                  Daily Pickup Coverage Report
                </CardTitle>
                <CardDescription>Pickup points coverage by ward, zone, and truck with completion status</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("daily_collection", "excel")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> Excel</Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("daily_collection", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Daily Pickup Coverage")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
                <Button variant="outline" size="sm" onClick={() => handlePrint("daily_collection")}>
                  <Printer className="h-4 w-4 mr-1" /> Print
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Status:</span>
                <div className="flex gap-1">
                  {["all", "completed", "partial"].map((status) => (
                    <Badge
                      key={status}
                      variant={dailyStatusFilter === status ? "default" : "outline"}
                      className={`cursor-pointer capitalize ${dailyStatusFilter === status ? "" : "hover:bg-muted"}`}
                      onClick={() => { setDailyStatusFilter(status); setDailyPage(1); }}
                    >
                      {status === "all" ? "All" : status}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <Card className="bg-emerald-500/10 border-emerald-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-emerald-600">{dailyTotalPoints}</p>
                    <p className="text-xs text-muted-foreground">Total Pickup Points</p>
                  </CardContent>
                </Card>
                <Card className="bg-green-500/10 border-green-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">{dailyCoveredPoints}</p>
                    <p className="text-xs text-muted-foreground">Covered</p>
                  </CardContent>
                </Card>
                <Card className="bg-red-500/10 border-red-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-red-600">{dailyMissedPoints}</p>
                    <p className="text-xs text-muted-foreground">Missed</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-500/10 border-blue-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-blue-600">-</p>
                    <p className="text-xs text-muted-foreground">Total Tons</p>
                  </CardContent>
                </Card>
                <Card className="bg-purple-500/10 border-purple-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-purple-600">{dailyCompletionPct.toFixed(1)}%</p>
                    <p className="text-xs text-muted-foreground">Completion</p>
                  </CardContent>
                </Card>
              </div>

              {/* Table */}
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead className="w-10"></TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Ward</TableHead>
                      <TableHead>Zone</TableHead>
                      <TableHead>Truck</TableHead>
                      <TableHead>Driver</TableHead>
                      <TableHead className="text-center">Pickup Points</TableHead>
                      <TableHead className="text-center">Covered</TableHead>
                      <TableHead className="text-center">Missed</TableHead>
                      <TableHead className="text-right">Weight (T)</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(() => {
                      const filteredData = dailyStatusFilter === "all" 
                        ? dailyPickupCoverageData 
                        : dailyPickupCoverageData.filter(d => d.status === dailyStatusFilter);
                      return paginate(filteredData, dailyPage).map((row) => {
                        const pickupDetails = Array.isArray(row.pickupDetails) ? row.pickupDetails : [];
                        const isExpanded = Boolean(expandedDailyRows[row.id]);

                        return (
                          <Fragment key={row.id}>
                            <TableRow>
                              <TableCell>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8"
                                  onClick={() => toggleDailyRow(row.id)}
                                  disabled={pickupDetails.length === 0}
                                  aria-label={isExpanded ? "Hide pickup point details" : "Show pickup point details"}
                                >
                                  <ChevronRight className={`h-4 w-4 transition-transform ${isExpanded ? "rotate-90" : ""}`} />
                                </Button>
                              </TableCell>
                              <TableCell className="font-medium">{row.date}</TableCell>
                              <TableCell>{row.ward}</TableCell>
                              <TableCell>{row.zone}</TableCell>
                              <TableCell className="font-mono text-xs">{row.truck}</TableCell>
                              <TableCell>{row.driver}</TableCell>
                              <TableCell className="text-center">{row.totalPoints}</TableCell>
                              <TableCell className="text-center text-green-600 font-medium">{row.covered}</TableCell>
                              <TableCell className="text-center text-red-600 font-medium">{row.missed}</TableCell>
                              <TableCell className="text-right">{row.weight}</TableCell>
                              <TableCell>
                                <Badge variant={row.status === "completed" ? "default" : "secondary"} 
                                       className={row.status === "completed" ? "bg-green-500/20 text-green-700 border-green-500/30" : "bg-yellow-500/20 text-yellow-700 border-yellow-500/30"}>
                                  {row.status}
                                </Badge>
                              </TableCell>
                            </TableRow>
                            {isExpanded && (
                              <TableRow className="bg-muted/20 hover:bg-muted/20">
                                <TableCell colSpan={11} className="p-0">
                                  <div className="p-4">
                                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                                      <div>
                                        <p className="text-sm font-semibold">Pickup Point Details</p>
                                        <p className="text-xs text-muted-foreground">
                                          Route: {row.route || "-"} | Truck: {row.truck} | Date: {row.date}
                                        </p>
                                      </div>
                                      <Badge variant="outline">{pickupDetails.length} points</Badge>
                                    </div>
                                    <div className="rounded-md border bg-background">
                                      <Table>
                                        <TableHeader>
                                          <TableRow className="bg-muted/50">
                                            <TableHead className="w-16 text-center">Seq</TableHead>
                                            <TableHead>Pickup Point</TableHead>
                                            <TableHead className="text-center">Expected</TableHead>
                                            <TableHead className="text-center">First Crossed</TableHead>
                                            <TableHead className="text-center">Last Crossed</TableHead>
                                            <TableHead className="text-center">Count</TableHead>
                                            <TableHead className="text-center">Nearest (m)</TableHead>
                                            <TableHead>Status</TableHead>
                                          </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                          {pickupDetails.length === 0 ? (
                                            <TableRow>
                                              <TableCell colSpan={8} className="py-6 text-center text-sm text-muted-foreground">
                                                No pickup point details available for this row.
                                              </TableCell>
                                            </TableRow>
                                          ) : (
                                            pickupDetails.map((point: any) => (
                                              <TableRow key={point.id}>
                                                <TableCell className="text-center font-mono text-xs">{point.sequenceNo || "-"}</TableCell>
                                                <TableCell className="font-medium">{point.pickupName || "-"}</TableCell>
                                                <TableCell className="text-center">{point.expectedTime || "-"}</TableCell>
                                                <TableCell className="text-center">{point.actualTime || "-"}</TableCell>
                                                <TableCell className="text-center">{point.lastCrossedTime || "-"}</TableCell>
                                                <TableCell className="text-center">{point.crossingCount || 0}</TableCell>
                                                <TableCell className="text-center">
                                                  {point.nearestDistanceM === null || point.nearestDistanceM === undefined
                                                    ? "-"
                                                    : Number(point.nearestDistanceM).toFixed(1)}
                                                </TableCell>
                                                <TableCell>
                                                  <Badge
                                                    variant={point.status === "covered" ? "default" : "secondary"}
                                                    className={point.status === "covered"
                                                      ? "bg-green-500/20 text-green-700 border-green-500/30"
                                                      : "bg-red-500/20 text-red-700 border-red-500/30"}
                                                  >
                                                    {point.status}
                                                  </Badge>
                                                </TableCell>
                                              </TableRow>
                                            ))
                                          )}
                                        </TableBody>
                                      </Table>
                                    </div>
                                  </div>
                                </TableCell>
                              </TableRow>
                            )}
                          </Fragment>
                        );
                      });
                    })()}
                  </TableBody>
                </Table>
              </div>
              {(() => {
                const filteredData = dailyStatusFilter === "all" 
                  ? dailyPickupCoverageData 
                  : dailyPickupCoverageData.filter(d => d.status === dailyStatusFilter);
                return renderPagination(dailyPage, filteredData.length, setDailyPage);
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Route Performance Report */}
        <TabsContent value="route" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Route className="h-5 w-5 text-primary" />
                  Route Performance Report
                </CardTitle>
                <CardDescription>Route completion rates, deviations, and efficiency metrics</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("route_performance", "excel")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> Excel</Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("route_performance", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Efficiency:</span>
                <div className="flex gap-1">
                  {[
                    { key: "all", label: "All" },
                    { key: "high", label: "High (≥90%)" },
                    { key: "medium", label: "Medium (80-89%)" },
                    { key: "low", label: "Low (<80%)" }
                  ].map((filter) => (
                    <Badge
                      key={filter.key}
                      variant={routeEfficiencyFilter === filter.key ? "default" : "outline"}
                      className={`cursor-pointer ${routeEfficiencyFilter === filter.key ? "" : "hover:bg-muted"}`}
                      onClick={() => { setRouteEfficiencyFilter(filter.key); setRoutePage(1); }}
                    >
                      {filter.label}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="bg-primary/10 border-primary/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-primary">94.6%</p>
                    <p className="text-xs text-muted-foreground">Avg Completion</p>
                  </CardContent>
                </Card>
                <Card className="bg-orange-500/10 border-orange-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-orange-600">19</p>
                    <p className="text-xs text-muted-foreground">Total Deviations</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-500/10 border-blue-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-blue-600">4.3 hrs</p>
                    <p className="text-xs text-muted-foreground">Avg Route Time</p>
                  </CardContent>
                </Card>
                <Card className="bg-green-500/10 border-green-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">91.2%</p>
                    <p className="text-xs text-muted-foreground">Avg Efficiency</p>
                  </CardContent>
                </Card>
              </div>

              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Route</TableHead>
                      <TableHead className="text-center">Completion %</TableHead>
                      <TableHead className="text-center">Avg Time</TableHead>
                      <TableHead className="text-center">Deviations</TableHead>
                      <TableHead>Efficiency</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(() => {
                      const filteredData = routePerformanceData.filter(row => {
                        if (routeEfficiencyFilter === "all") return true;
                        if (routeEfficiencyFilter === "high") return row.efficiency >= 90;
                        if (routeEfficiencyFilter === "medium") return row.efficiency >= 80 && row.efficiency < 90;
                        return row.efficiency < 80;
                      });
                      return paginate(filteredData, routePage).map((row, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{row.route}</TableCell>
                          <TableCell className="text-center">
                            <div className="flex items-center gap-2 justify-center">
                              <span className={row.completion >= 95 ? "text-green-600" : row.completion >= 90 ? "text-yellow-600" : "text-red-600"}>
                                {row.completion}%
                              </span>
                              {row.completion >= 95 ? <TrendingUp className="h-4 w-4 text-green-600" /> : <TrendingDown className="h-4 w-4 text-red-600" />}
                            </div>
                          </TableCell>
                          <TableCell className="text-center">{row.avgTime}</TableCell>
                          <TableCell className="text-center">
                            <Badge variant={row.deviations === 0 ? "default" : "destructive"} className={row.deviations === 0 ? "bg-green-500/20 text-green-700" : ""}>
                              {row.deviations}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={row.efficiency} className="h-2 w-20" />
                              <span className="text-sm font-medium">{row.efficiency}%</span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ));
                    })()}
                  </TableBody>
                </Table>
              </div>
              {(() => {
                const filteredData = routePerformanceData.filter(row => {
                  if (routeEfficiencyFilter === "all") return true;
                  if (routeEfficiencyFilter === "high") return row.efficiency >= 90;
                  if (routeEfficiencyFilter === "medium") return row.efficiency >= 80 && row.efficiency < 90;
                  return row.efficiency < 80;
                });
                return renderPagination(routePage, filteredData.length, setRoutePage);
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Truck Utilization Report */}
        <TabsContent value="truck" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Truck className="h-5 w-5 text-primary" />
                  Truck Utilization Report
                </CardTitle>
                <CardDescription>Trips, operating hours, idle time, and vehicle utilization</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("truck_utilization", "excel")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> Excel</Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("truck_utilization", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Type:</span>
                <div className="flex gap-1">
                  {["all", "Compactor", "Mini Truck", "Dumper", "Open Truck"].map((type) => (
                    <Badge
                      key={type}
                      variant={truckTypeFilter === type ? "default" : "outline"}
                      className={`cursor-pointer ${truckTypeFilter === type ? "" : "hover:bg-muted"}`}
                      onClick={() => { setTruckTypeFilter(type); setTruckPage(1); }}
                    >
                      {type === "all" ? "All Types" : type}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="bg-primary/10 border-primary/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-primary">15</p>
                    <p className="text-xs text-muted-foreground">Total Trips</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-500/10 border-blue-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-blue-600">41.5 hrs</p>
                    <p className="text-xs text-muted-foreground">Operating Hours</p>
                  </CardContent>
                </Card>
                <Card className="bg-orange-500/10 border-orange-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-orange-600">6.1 hrs</p>
                    <p className="text-xs text-muted-foreground">Total Idle Time</p>
                  </CardContent>
                </Card>
                <Card className="bg-green-500/10 border-green-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">89.2%</p>
                    <p className="text-xs text-muted-foreground">Avg Utilization</p>
                  </CardContent>
                </Card>
              </div>

              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Truck</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead className="text-center">Trips</TableHead>
                      <TableHead className="text-center">Operating Hrs</TableHead>
                      <TableHead className="text-center">Idle Time</TableHead>
                      <TableHead className="text-center">Distance (km)</TableHead>
                      <TableHead>Utilization</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(() => {
                      const filteredData = truckTypeFilter === "all" 
                        ? truckUtilizationData 
                        : truckUtilizationData.filter(d => d.type === truckTypeFilter);
                      return paginate(filteredData, truckPage).map((row, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-mono text-xs font-medium">{row.truck}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{row.type}</Badge>
                          </TableCell>
                          <TableCell className="text-center">{row.trips}</TableCell>
                          <TableCell className="text-center">{row.operatingHours}</TableCell>
                          <TableCell className="text-center">
                            <span className={row.idleTime > 1.5 ? "text-red-600" : "text-green-600"}>
                              {row.idleTime} hrs
                            </span>
                          </TableCell>
                          <TableCell className="text-center">{row.distance}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={row.utilization} className="h-2 w-20" />
                              <span className={`text-sm font-medium ${row.utilization >= 90 ? "text-green-600" : row.utilization >= 80 ? "text-yellow-600" : "text-red-600"}`}>
                                {row.utilization}%
                              </span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ));
                    })()}
                  </TableBody>
                </Table>
              </div>
              {(() => {
                const filteredData = truckTypeFilter === "all" 
                  ? truckUtilizationData 
                  : truckUtilizationData.filter(d => d.type === truckTypeFilter);
                return renderPagination(truckPage, filteredData.length, setTruckPage);
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trips Completed Report */}
        <TabsContent value="trips-completed" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-primary" />
                  Trips Completed Report
                </CardTitle>
                <CardDescription>Completed trips by truck using route visit, GTC entry, and halt-time logic</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("trips_completed", "excel")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> Excel</Button>
                <Button variant="outline" size="sm" onClick={() => handlePrint("trips_completed")}>
                  <Printer className="h-4 w-4 mr-1" /> Print
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="bg-green-500/10 border-green-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">{tripTotalCompleted}</p>
                    <p className="text-xs text-muted-foreground">Trips Completed</p>
                  </CardContent>
                </Card>
                <Card className="bg-primary/10 border-primary/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-primary">{new Set(tripCompletedData.map(row => row.truck)).size}</p>
                    <p className="text-xs text-muted-foreground">Trucks Completed</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-500/10 border-blue-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-blue-600">{tripAvgMinutes}m</p>
                    <p className="text-xs text-muted-foreground">Avg Trip Time</p>
                  </CardContent>
                </Card>
                <Card className="bg-amber-500/10 border-amber-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-amber-600">{tripTotalPickupPoints}</p>
                    <p className="text-xs text-muted-foreground">Route Points</p>
                  </CardContent>
                </Card>
              </div>

              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead className="w-10"></TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Truck</TableHead>
                      <TableHead>Route</TableHead>
                      <TableHead>Zone</TableHead>
                      <TableHead>Ward</TableHead>
                      <TableHead className="text-center">Start</TableHead>
                      <TableHead className="text-center">GTC Entry</TableHead>
                      <TableHead className="text-center">Duration</TableHead>
                      <TableHead className="text-center">GTC Point</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginate(tripCompletedData, tripPage).map((row, idx) => {
                      const rowId = row.id || `trip-${idx}`;
                      const tripDetails = Array.isArray(row.tripDetails) ? row.tripDetails : [];
                      const isExpanded = Boolean(expandedTripRows[rowId]);

                      return (
                        <Fragment key={rowId}>
                          <TableRow>
                            <TableCell>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => toggleTripRow(rowId)}
                                disabled={tripDetails.length === 0}
                                aria-label={isExpanded ? "Hide trip details" : "Show trip details"}
                              >
                                <ChevronRight className={`h-4 w-4 transition-transform ${isExpanded ? "rotate-90" : ""}`} />
                              </Button>
                            </TableCell>
                            <TableCell className="font-medium">{row.date}</TableCell>
                            <TableCell className="font-mono text-xs">{row.truck}</TableCell>
                            <TableCell>{row.route}</TableCell>
                            <TableCell>{row.zone}</TableCell>
                            <TableCell>{row.ward}</TableCell>
                            <TableCell className="text-center">{row.startTime}</TableCell>
                            <TableCell className="text-center">{row.endTime}</TableCell>
                            <TableCell className="text-center">{row.duration}</TableCell>
                            <TableCell className="text-center">{row.gtcPoint || "-"}</TableCell>
                            <TableCell>
                              <Badge className="bg-green-500/20 text-green-700 border-green-500/30">
                                completed
                              </Badge>
                            </TableCell>
                          </TableRow>
                          {isExpanded && (
                            <TableRow className="bg-muted/20 hover:bg-muted/20">
                              <TableCell colSpan={11} className="p-0">
                                <div className="p-4">
                                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                                    <div>
                                      <p className="text-sm font-semibold">Trip Details</p>
                                      <p className="text-xs text-muted-foreground">
                                        Trip: {row.id || "-"} | Truck: {row.truck} | Route: {row.route || "-"} | Halt rule: {row.haltSeconds || 0}s inside {row.gtcRadiusM || 0}m GTC
                                      </p>
                                    </div>
                                    <Badge variant="outline">{tripDetails.length} route points</Badge>
                                  </div>
                                  <div className="rounded-md border bg-background">
                                    <Table>
                                      <TableHeader>
                                        <TableRow className="bg-muted/50">
                                          <TableHead className="w-16 text-center">Seq</TableHead>
                                          <TableHead>Pickup Point</TableHead>
                                          <TableHead className="text-center">Expected</TableHead>
                                          <TableHead className="text-center">First Crossed</TableHead>
                                          <TableHead className="text-center">Last Crossed</TableHead>
                                          <TableHead className="text-center">Count</TableHead>
                                          <TableHead className="text-center">Nearest (m)</TableHead>
                                          <TableHead>Status</TableHead>
                                        </TableRow>
                                      </TableHeader>
                                      <TableBody>
                                        {tripDetails.length === 0 ? (
                                          <TableRow>
                                            <TableCell colSpan={8} className="py-6 text-center text-sm text-muted-foreground">
                                              No detail rows available for this trip.
                                            </TableCell>
                                          </TableRow>
                                        ) : (
                                          tripDetails.map((point: any) => (
                                            <TableRow key={point.id}>
                                              <TableCell className="text-center font-mono text-xs">{point.sequenceNo || "-"}</TableCell>
                                              <TableCell className="font-medium">
                                                <div className="flex flex-wrap items-center gap-2">
                                                  <span>{point.pickupName || "-"}</span>
                                                  {point.isGtcPoint && (
                                                    <Badge variant="outline" className="border-blue-500/30 bg-blue-500/10 text-blue-700">
                                                      GTC
                                                    </Badge>
                                                  )}
                                                </div>
                                              </TableCell>
                                              <TableCell className="text-center">{point.expectedTime || "-"}</TableCell>
                                              <TableCell className="text-center">{point.actualTime || "-"}</TableCell>
                                              <TableCell className="text-center">{point.lastCrossedTime || "-"}</TableCell>
                                              <TableCell className="text-center">{point.crossingCount || 0}</TableCell>
                                              <TableCell className="text-center">
                                                {point.nearestDistanceM === null || point.nearestDistanceM === undefined
                                                  ? "-"
                                                  : Number(point.nearestDistanceM).toFixed(1)}
                                              </TableCell>
                                              <TableCell>
                                                <Badge
                                                  variant={point.status === "covered" ? "default" : "secondary"}
                                                  className={point.status === "covered"
                                                    ? "bg-green-500/20 text-green-700 border-green-500/30"
                                                    : "bg-red-500/20 text-red-700 border-red-500/30"}
                                                >
                                                  {point.status}
                                                </Badge>
                                              </TableCell>
                                            </TableRow>
                                          ))
                                        )}
                                      </TableBody>
                                    </Table>
                                  </div>
                                </div>
                              </TableCell>
                            </TableRow>
                          )}
                        </Fragment>
                      );
                    })}
                    {tripCompletedData.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={11} className="text-center text-muted-foreground">
                          No completed trips found for the selected filters.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
              {renderPagination(tripPage, tripCompletedData.length, setTripPage)}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Fuel Consumption Report */}
        <TabsContent value="fuel" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Fuel className="h-5 w-5 text-primary" />
                  Fuel Consumption Report
                </CardTitle>
                <CardDescription>Fuel usage, efficiency metrics, anomaly detection, and costs</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("fuel_consumption", "excel")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> Excel</Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("fuel_consumption", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Status:</span>
                <div className="flex gap-1">
                  {[
                    { key: "all", label: "All" },
                    { key: "normal", label: "Normal" },
                    { key: "anomaly", label: "Anomalies" }
                  ].map((filter) => (
                    <Badge
                      key={filter.key}
                      variant={fuelAnomalyFilter === filter.key ? "default" : "outline"}
                      className={`cursor-pointer ${fuelAnomalyFilter === filter.key ? "" : "hover:bg-muted"}`}
                      onClick={() => { setFuelAnomalyFilter(filter.key); setFuelPage(1); }}
                    >
                      {filter.label}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <Card className="bg-primary/10 border-primary/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-primary">105L</p>
                    <p className="text-xs text-muted-foreground">Total Fuel</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-500/10 border-blue-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-blue-600">224 km</p>
                    <p className="text-xs text-muted-foreground">Total Distance</p>
                  </CardContent>
                </Card>
                <Card className="bg-green-500/10 border-green-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">2.21</p>
                    <p className="text-xs text-muted-foreground">Avg km/L</p>
                  </CardContent>
                </Card>
                <Card className="bg-orange-500/10 border-orange-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-orange-600">₹10,500</p>
                    <p className="text-xs text-muted-foreground">Total Cost</p>
                  </CardContent>
                </Card>
                <Card className="bg-red-500/10 border-red-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-red-600">1</p>
                    <p className="text-xs text-muted-foreground">Anomalies</p>
                  </CardContent>
                </Card>
              </div>

              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Truck</TableHead>
                      <TableHead className="text-center">Fuel (L)</TableHead>
                      <TableHead className="text-center">Distance (km)</TableHead>
                      <TableHead className="text-center">Efficiency (km/L)</TableHead>
                      <TableHead className="text-right">Cost (₹)</TableHead>
                      <TableHead className="text-center">Anomaly</TableHead>
                      <TableHead>Score</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(() => {
                      const filteredData = fuelConsumptionData.filter(row => {
                        if (fuelAnomalyFilter === "all") return true;
                        if (fuelAnomalyFilter === "anomaly") return row.anomaly;
                        return !row.anomaly;
                      });
                      return paginate(filteredData, fuelPage).map((row, idx) => (
                        <TableRow key={idx} className={row.anomaly ? "bg-red-500/5" : ""}>
                          <TableCell className="font-mono text-xs font-medium">{row.truck}</TableCell>
                          <TableCell className="text-center">{row.fuelUsed}</TableCell>
                          <TableCell className="text-center">{row.distance}</TableCell>
                          <TableCell className="text-center">
                            <span className={row.efficiency >= 2.0 ? "text-green-600" : "text-red-600"}>
                              {row.efficiency.toFixed(2)}
                            </span>
                          </TableCell>
                          <TableCell className="text-right">₹{row.cost.toLocaleString()}</TableCell>
                          <TableCell className="text-center">
                            {row.anomaly ? (
                              <Badge variant="destructive" className="gap-1">
                                <AlertTriangle className="h-3 w-3" /> Detected
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="bg-green-500/20 text-green-700 border-green-500/30">Normal</Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={row.score} className="h-2 w-16" />
                              <span className={`text-sm font-medium ${row.score >= 80 ? "text-green-600" : row.score >= 60 ? "text-yellow-600" : "text-red-600"}`}>
                                {row.score}
                              </span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ));
                    })()}
                  </TableBody>
                </Table>
              </div>
              {(() => {
                const filteredData = fuelConsumptionData.filter(row => {
                  if (fuelAnomalyFilter === "all") return true;
                  if (fuelAnomalyFilter === "anomaly") return row.anomaly;
                  return !row.anomaly;
                });
                return renderPagination(fuelPage, filteredData.length, setFuelPage);
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Driver Attendance Report */}
        <TabsContent value="driver" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-primary" />
                  Driver Attendance & Performance Report
                </CardTitle>
                <CardDescription>Shift timings, routes completed, violations, and driver scores</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("driver_attendance", "excel")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> Excel</Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("driver_attendance", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Attendance:</span>
                <div className="flex gap-1">
                  {[
                    { key: "all", label: "All" },
                    { key: "on-time", label: "On Time" },
                    { key: "late", label: "Late" }
                  ].map((filter) => (
                    <Badge
                      key={filter.key}
                      variant={driverOnTimeFilter === filter.key ? "default" : "outline"}
                      className={`cursor-pointer ${driverOnTimeFilter === filter.key ? "" : "hover:bg-muted"}`}
                      onClick={() => { setDriverOnTimeFilter(filter.key); setDriverPage(1); }}
                    >
                      {filter.label}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="bg-primary/10 border-primary/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-primary">5</p>
                    <p className="text-xs text-muted-foreground">Active Drivers</p>
                  </CardContent>
                </Card>
                <Card className="bg-green-500/10 border-green-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">41 hrs</p>
                    <p className="text-xs text-muted-foreground">Total Hours</p>
                  </CardContent>
                </Card>
                <Card className="bg-red-500/10 border-red-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-red-600">4</p>
                    <p className="text-xs text-muted-foreground">Violations</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-500/10 border-blue-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-blue-600">87</p>
                    <p className="text-xs text-muted-foreground">Avg Score</p>
                  </CardContent>
                </Card>
              </div>

              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Driver</TableHead>
                      <TableHead>ID</TableHead>
                      <TableHead className="text-center">Shift Start</TableHead>
                      <TableHead className="text-center">Shift End</TableHead>
                      <TableHead className="text-center">Hours</TableHead>
                      <TableHead className="text-center">Routes</TableHead>
                      <TableHead className="text-center">On Time</TableHead>
                      <TableHead className="text-center">Violations</TableHead>
                      <TableHead>Score</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(() => {
                      const filteredData = driverAttendanceData.filter(row => {
                        if (driverOnTimeFilter === "all") return true;
                        if (driverOnTimeFilter === "on-time") return row.onTime;
                        return !row.onTime;
                      });
                      return paginate(filteredData, driverPage).map((row, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{row.driver}</TableCell>
                          <TableCell className="font-mono text-xs">{row.id}</TableCell>
                          <TableCell className="text-center">{row.shiftStart}</TableCell>
                          <TableCell className="text-center">{row.shiftEnd}</TableCell>
                          <TableCell className="text-center">{row.hoursWorked}</TableCell>
                          <TableCell className="text-center">{row.routes}</TableCell>
                          <TableCell className="text-center">
                            {row.onTime ? (
                              <Badge className="bg-green-500/20 text-green-700 border-green-500/30">Yes</Badge>
                            ) : (
                              <Badge variant="destructive">Late</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-center">
                            <span className={row.violations > 0 ? "text-red-600 font-medium" : "text-green-600"}>
                              {row.violations}
                            </span>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={row.score} className="h-2 w-16" />
                              <span className={`text-sm font-medium ${row.score >= 90 ? "text-green-600" : row.score >= 75 ? "text-yellow-600" : "text-red-600"}`}>
                                {row.score}
                              </span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ));
                    })()}
                  </TableBody>
                </Table>
              </div>
              {(() => {
                const filteredData = driverAttendanceData.filter(row => {
                  if (driverOnTimeFilter === "all") return true;
                  if (driverOnTimeFilter === "on-time") return row.onTime;
                  return !row.onTime;
                });
                return renderPagination(driverPage, filteredData.length, setDriverPage);
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* First Pickup Entry Report */}
        <TabsContent value="late-arrival" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-primary" />
                  First Pickup Entry Report
                </CardTitle>
                <CardDescription>
                  First pickup point entry by date, route, and truck. Late means actual entry is after expected time + grace.
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("late_arrival", "excel")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> Excel</Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("late_arrival", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {(() => {
                const allData = lateArrivalData.filter(row => {
                  const zoneMatch = lateZoneFilter === "all" || row.zone === lateZoneFilter;
                  const wardMatch = lateWardFilter === "all" || row.ward === lateWardFilter;
                  const vendorMatch = lateVendorFilter === "all" || row.vendor === lateVendorFilter;
                  const routeTypeMatch = lateRouteTypeFilter === "all" || row.routeType === lateRouteTypeFilter;
                  return zoneMatch && wardMatch && vendorMatch && routeTypeMatch;
                });
                const filteredByStatus = allData.filter(row => {
                  if (lateStatusFilter === "all") return true;
                  const isLate = Boolean(row.isLate);
                  if (lateStatusFilter === "late") return isLate;
                  return !isLate;
                });
                const lateCount = allData.filter(d => d.isLate).length;
                const onTimeCount = allData.filter(d => !d.isLate).length;
                const avgDelay = Math.round(allData.filter(d => d.isLate).reduce((sum, d) => sum + (Number(d.lateByMinutes) || 0), 0) / Math.max(lateCount, 1));
                const graceMinutes = allData.find(d => d.graceMinutes !== undefined)?.graceMinutes ?? 15;

                const uniqueZones = [...new Set(lateArrivalData.map(d => d.zone))];
                const uniqueWards = [...new Set(lateArrivalData.filter(d => lateZoneFilter === "all" || d.zone === lateZoneFilter).map(d => d.ward))];
                const uniqueVendors = [...new Set(lateArrivalData.map(d => d.vendor))];
                const uniqueRouteTypes = [...new Set(lateArrivalData.map(d => d.routeType).filter(Boolean))];

                return (
                  <>
                    {/* Filters */}
                    <div className="flex flex-wrap items-center gap-3">
                      <Select value={lateZoneFilter} onValueChange={(v) => { setLateZoneFilter(v); setLateWardFilter("all"); setLateArrivalPage(1); }}>
                        <SelectTrigger className="w-[160px] h-8 text-xs">
                          <SelectValue placeholder="Zone" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Zones</SelectItem>
                          {uniqueZones.map(z => <SelectItem key={z} value={z}>{z}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <Select value={lateWardFilter} onValueChange={(v) => { setLateWardFilter(v); setLateArrivalPage(1); }}>
                        <SelectTrigger className="w-[160px] h-8 text-xs">
                          <SelectValue placeholder="Ward" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Wards</SelectItem>
                          {uniqueWards.map(w => <SelectItem key={w} value={w}>{w}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <Select value={lateVendorFilter} onValueChange={(v) => { setLateVendorFilter(v); setLateArrivalPage(1); }}>
                        <SelectTrigger className="w-[180px] h-8 text-xs">
                          <SelectValue placeholder="Vendor" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Vendors</SelectItem>
                          {uniqueVendors.map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <Select value={lateRouteTypeFilter} onValueChange={(v) => { setLateRouteTypeFilter(v); setLateArrivalPage(1); }}>
                        <SelectTrigger className="w-[160px] h-8 text-xs">
                          <SelectValue placeholder="Route Type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Types</SelectItem>
                          {uniqueRouteTypes.map(type => <SelectItem key={type} value={type}>{type}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Status Filter */}
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-muted-foreground">Filter by Status:</span>
                      <div className="flex gap-1">
                        {[
                          { key: "all", label: "All" },
                          { key: "on-time", label: "On Time" },
                          { key: "late", label: `Late > ${graceMinutes} min grace` }
                        ].map((filter) => (
                          <Badge
                            key={filter.key}
                            variant={lateStatusFilter === filter.key ? "default" : "outline"}
                            className={`cursor-pointer ${filter.key === "late" ? "text-red-600 border-red-500/40" : ""} ${lateStatusFilter === filter.key ? "" : "hover:bg-muted"}`}
                            onClick={() => { setLateStatusFilter(filter.key); setLateArrivalPage(1); }}
                          >
                            {filter.label}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <Card className="bg-green-500/10 border-green-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-green-600">{onTimeCount}</p>
                          <p className="text-xs text-muted-foreground">On Time</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-red-500/10 border-red-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-red-600">{lateCount}</p>
                          <p className="text-xs text-muted-foreground">Late Arrivals</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-orange-500/10 border-orange-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-orange-600">{avgDelay} min</p>
                          <p className="text-xs text-muted-foreground">Avg Delay</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-primary/10 border-primary/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-primary">{allData.length > 0 ? Math.round((onTimeCount / allData.length) * 100) : 0}%</p>
                          <p className="text-xs text-muted-foreground">On-Time Rate</p>
                        </CardContent>
                      </Card>
                    </div>

                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-muted/50">
                            <TableHead>Date</TableHead>
                            <TableHead>Zone</TableHead>
                            <TableHead>Truck</TableHead>
                            <TableHead>Driver</TableHead>
                            <TableHead>Route</TableHead>
                            <TableHead>First Pickup</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead className="text-center">Expected</TableHead>
                            <TableHead className="text-center">Allowed Until</TableHead>
                            <TableHead className="text-center">Actual Entry</TableHead>
                            <TableHead className="text-center">Late By</TableHead>
                            <TableHead>Reason</TableHead>
                            <TableHead>Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {paginate(filteredByStatus, lateArrivalPage).map((row) => {
                            const isLate = Boolean(row.isLate);
                            return (
                              <TableRow key={row.id} className={isLate ? "bg-red-500/5" : ""}>
                                <TableCell className="font-medium">{row.date}</TableCell>
                                <TableCell className="text-xs">{row.zone}</TableCell>
                                <TableCell className="font-mono text-xs">{row.truck}</TableCell>
                                <TableCell>{row.driver}</TableCell>
                                <TableCell>{row.route}</TableCell>
                                <TableCell>
                                  <div className="text-sm font-medium">{row.firstPickupPoint || "-"}</div>
                                  <div className="text-xs text-muted-foreground">Seq {row.firstPickupSequence || "-"}</div>
                                </TableCell>
                                <TableCell>
                                  <Badge variant="outline" className="text-xs">
                                    {row.routeType || "-"}
                                  </Badge>
                                </TableCell>
                                <TableCell className="text-center">{row.scheduledTime}</TableCell>
                                <TableCell className="text-center">{row.allowedUntil || "-"}</TableCell>
                                <TableCell className="text-center">{row.actualTime}</TableCell>
                                <TableCell className="text-center">
                                  <span className={`font-medium ${isLate ? "text-red-600" : "text-green-600"}`}>
                                    {isLate ? `${row.lateByMinutes || 0} min` : "0 min"}
                                  </span>
                                </TableCell>
                                <TableCell className="text-xs text-muted-foreground">{row.reason || "-"}</TableCell>
                                <TableCell>
                                  <Badge className={isLate ? "bg-red-500/20 text-red-700 border-red-500/30" : "bg-green-500/20 text-green-700 border-green-500/30"}>
                                    {isLate ? "Late" : "On Time"}
                                  </Badge>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                          {filteredByStatus.length === 0 && (
                            <TableRow>
                              <TableCell colSpan={13} className="py-6 text-center text-sm text-muted-foreground">
                                No first pickup entry records found for the selected filters.
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </div>
                    {renderPagination(lateArrivalPage, filteredByStatus.length, setLateArrivalPage)}
                  </>
                );
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Driver Behavior Report */}
        <TabsContent value="behavior" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Gauge className="h-5 w-5 text-primary" />
                  Driver Behavior Report
                </CardTitle>
                <CardDescription>Overspeeding, harsh braking, and rapid acceleration incidents</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("driver_behavior", "excel")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> Excel</Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("driver_behavior", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Driver Behavior")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground">Type:</span>
                  <div className="flex gap-1">
                    {[
                      { key: "all", label: "All" },
                      { key: "Overspeeding", label: "Overspeeding" },
                      { key: "Harsh Braking", label: "Harsh Braking" },
                      { key: "Rapid Acceleration", label: "Rapid Accel" }
                    ].map((filter) => (
                      <Badge
                        key={filter.key}
                        variant={behaviorTypeFilter === filter.key ? "default" : "outline"}
                        className={`cursor-pointer ${behaviorTypeFilter === filter.key ? "" : "hover:bg-muted"}`}
                        onClick={() => { setBehaviorTypeFilter(filter.key); setBehaviorPage(1); }}
                      >
                        {filter.label}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground">Severity:</span>
                  <div className="flex gap-1">
                    {[
                      { key: "all", label: "All" },
                      { key: "high", label: "High" },
                      { key: "medium", label: "Medium" },
                      { key: "low", label: "Low" }
                    ].map((filter) => (
                      <Badge
                        key={filter.key}
                        variant={behaviorSeverityFilter === filter.key ? "default" : "outline"}
                        className={`cursor-pointer ${behaviorSeverityFilter === filter.key ? "" : "hover:bg-muted"}`}
                        onClick={() => { setBehaviorSeverityFilter(filter.key); setBehaviorPage(1); }}
                      >
                        {filter.label}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              {(() => {
                const filteredData = driverBehaviorData.filter(row => {
                  const typeMatch = behaviorTypeFilter === "all" || row.incidentType === behaviorTypeFilter;
                  const severityMatch = behaviorSeverityFilter === "all" || row.severity === behaviorSeverityFilter;
                  return typeMatch && severityMatch;
                });
                
                const overspeedCount = filteredData.filter(d => d.incidentType === "Overspeeding").length;
                const harshBrakingCount = filteredData.filter(d => d.incidentType === "Harsh Braking").length;
                const rapidAccelCount = filteredData.filter(d => d.incidentType === "Rapid Acceleration").length;
                const highSeverityCount = filteredData.filter(d => d.severity === "high").length;

                return (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <Card className="bg-red-500/10 border-red-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-red-600">{overspeedCount}</p>
                          <p className="text-xs text-muted-foreground">Overspeeding</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-orange-500/10 border-orange-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-orange-600">{harshBrakingCount}</p>
                          <p className="text-xs text-muted-foreground">Harsh Braking</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-yellow-500/10 border-yellow-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-yellow-600">{rapidAccelCount}</p>
                          <p className="text-xs text-muted-foreground">Rapid Acceleration</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-purple-500/10 border-purple-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-purple-600">{highSeverityCount}</p>
                          <p className="text-xs text-muted-foreground">High Severity</p>
                        </CardContent>
                      </Card>
                    </div>

                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-muted/50">
                            <TableHead>Date</TableHead>
                            <TableHead>Time</TableHead>
                            <TableHead>Truck</TableHead>
                            <TableHead>Driver</TableHead>
                            <TableHead>Incident Type</TableHead>
                            <TableHead className="text-center">Recorded</TableHead>
                            <TableHead className="text-center">Limit</TableHead>
                            <TableHead>Location</TableHead>
                            <TableHead>Severity</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {paginate(filteredData, behaviorPage).map((row) => (
                            <TableRow key={row.id} className={row.severity === "high" ? "bg-red-500/5" : ""}>
                              <TableCell className="font-medium">{row.date}</TableCell>
                              <TableCell>{row.time}</TableCell>
                              <TableCell className="font-mono text-xs">{row.truck}</TableCell>
                              <TableCell>{row.driver}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className="gap-1">
                                  {row.incidentType === "Overspeeding" && <Zap className="h-3 w-3" />}
                                  {row.incidentType === "Harsh Braking" && <AlertTriangle className="h-3 w-3" />}
                                  {row.incidentType === "Rapid Acceleration" && <TrendingUp className="h-3 w-3" />}
                                  {row.incidentType}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-center text-red-600 font-medium">{row.value}</TableCell>
                              <TableCell className="text-center text-muted-foreground">{row.limit}</TableCell>
                              <TableCell className="text-xs">{row.location}</TableCell>
                              <TableCell>
                                <Badge 
                                  className={
                                    row.severity === "high" 
                                      ? "bg-red-500/20 text-red-700 border-red-500/30"
                                      : row.severity === "medium"
                                      ? "bg-orange-500/20 text-orange-700 border-orange-500/30"
                                      : "bg-yellow-500/20 text-yellow-700 border-yellow-500/30"
                                  }
                                >
                                  {row.severity}
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    {renderPagination(behaviorPage, filteredData.length, setBehaviorPage)}
                  </>
                );
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Vehicle Status Report */}
        <TabsContent value="vehicle-status" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <WifiOff className="h-5 w-5 text-primary" />
                  Vehicle Status Report
                </CardTitle>
                <CardDescription>Live status of all vehicles including inactive and failed devices</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("vehicle_status", "excel")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> Excel</Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("vehicle_status", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Vehicle Status")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Status:</span>
                <div className="flex gap-1">
                  {[
                    { key: "all", label: "All" },
                    { key: "active", label: "Active" },
                    { key: "warning", label: "Warning" },
                    { key: "inactive", label: "Inactive" },
                    { key: "failed", label: "Failed" }
                  ].map((filter) => (
                    <Badge
                      key={filter.key}
                      variant={vehicleStatusFilter === filter.key ? "default" : "outline"}
                      className={`cursor-pointer ${vehicleStatusFilter === filter.key ? "" : "hover:bg-muted"}`}
                      onClick={() => { setVehicleStatusFilter(filter.key); setVehicleStatusPage(1); }}
                    >
                      {filter.label}
                    </Badge>
                  ))}
                </div>
              </div>

              {(() => {
                const filteredData = vehicleStatusFilter === "all" 
                  ? vehicleStatusData 
                  : vehicleStatusData.filter(d => d.status === vehicleStatusFilter);
                  
                const activeCount = filteredData.filter(d => d.status === "active").length;
                const inactiveCount = filteredData.filter(d => d.status === "inactive").length;
                const warningCount = filteredData.filter(d => d.status === "warning").length;
                const failedCount = filteredData.filter(d => d.status === "failed").length;

                return (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <Card className="bg-green-500/10 border-green-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-green-600">{activeCount}</p>
                          <p className="text-xs text-muted-foreground">Active</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-yellow-500/10 border-yellow-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-yellow-600">{warningCount}</p>
                          <p className="text-xs text-muted-foreground">Warning</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-gray-500/10 border-gray-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-gray-600">{inactiveCount}</p>
                          <p className="text-xs text-muted-foreground">Inactive</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-red-500/10 border-red-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-red-600">{failedCount}</p>
                          <p className="text-xs text-muted-foreground">Failed</p>
                        </CardContent>
                      </Card>
                    </div>

                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-muted/50">
                            <TableHead>Truck</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead>Driver</TableHead>
                            <TableHead>Route</TableHead>
                            <TableHead>GPS Status</TableHead>
                            <TableHead className="text-center">Battery</TableHead>
                            <TableHead className="text-center">Signal</TableHead>
                            <TableHead>Last Update</TableHead>
                            <TableHead>Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {paginate(filteredData, vehicleStatusPage).map((row) => (
                            <TableRow key={row.id} className={row.status === "failed" || row.status === "inactive" ? "bg-red-500/5" : ""}>
                              <TableCell className="font-mono text-xs font-medium">{row.truck}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className="capitalize">{row.type}</Badge>
                              </TableCell>
                              <TableCell>{row.driver}</TableCell>
                              <TableCell>{row.route}</TableCell>
                              <TableCell>
                                <Badge 
                                  className={
                                    row.gpsStatus === "online"
                                      ? "bg-green-500/20 text-green-700 border-green-500/30"
                                      : row.gpsStatus === "warning"
                                      ? "bg-yellow-500/20 text-yellow-700 border-yellow-500/30"
                                      : "bg-red-500/20 text-red-700 border-red-500/30"
                                  }
                                >
                                  {row.gpsStatus === "online" ? "Online" : row.gpsStatus === "warning" ? "Weak Signal" : "Offline"}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-center">
                                <div className="flex items-center justify-center gap-1">
                                  <Progress value={row.batteryLevel} className="h-2 w-12" />
                                  <span className={`text-xs font-medium ${row.batteryLevel < 20 ? "text-red-600" : row.batteryLevel < 50 ? "text-yellow-600" : "text-green-600"}`}>
                                    {row.batteryLevel}%
                                  </span>
                                </div>
                              </TableCell>
                              <TableCell className="text-center">
                                <span className={`font-medium ${row.signalStrength < 30 ? "text-red-600" : row.signalStrength < 60 ? "text-yellow-600" : "text-green-600"}`}>
                                  {row.signalStrength}%
                                </span>
                              </TableCell>
                              <TableCell className="text-xs text-muted-foreground">{row.lastUpdate}</TableCell>
                              <TableCell>
                                <Badge 
                                  className={
                                    row.status === "active"
                                      ? "bg-green-500/20 text-green-700 border-green-500/30"
                                      : row.status === "warning"
                                      ? "bg-yellow-500/20 text-yellow-700 border-yellow-500/30"
                                      : row.status === "inactive"
                                      ? "bg-gray-500/20 text-gray-700 border-gray-500/30"
                                      : "bg-red-500/20 text-red-700 border-red-500/30"
                                  }
                                >
                                  {row.status === "failed" && <XCircle className="h-3 w-3 mr-1" />}
                                  {row.status === "inactive" && <WifiOff className="h-3 w-3 mr-1" />}
                                  {row.status.charAt(0).toUpperCase() + row.status.slice(1)}
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    {renderPagination(vehicleStatusPage, filteredData.length, setVehicleStatusPage)}
                  </>
                );
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Complaints Report */}
        <TabsContent value="complaints" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-primary" />
                  Citizen Complaints Report
                </CardTitle>
                <CardDescription>Complaints mapped to truck movements and response times</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("complaints", "excel")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> Excel</Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("complaints", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Complaints")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground">Status:</span>
                  <div className="flex gap-1">
                    {[
                      { key: "all", label: "All" },
                      { key: "resolved", label: "Resolved" },
                      { key: "in-progress", label: "In Progress" },
                      { key: "pending", label: "Pending" }
                    ].map((filter) => (
                      <Badge
                        key={filter.key}
                        variant={complaintsStatusFilter === filter.key ? "default" : "outline"}
                        className={`cursor-pointer ${complaintsStatusFilter === filter.key ? "" : "hover:bg-muted"}`}
                        onClick={() => { setComplaintsStatusFilter(filter.key); setComplaintsPage(1); }}
                      >
                        {filter.label}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground">Type:</span>
                  <div className="flex gap-1">
                    {[
                      { key: "all", label: "All" },
                      { key: "Missed Pickup", label: "Missed Pickup" },
                      { key: "Irregular Timing", label: "Irregular Timing" },
                      { key: "Spillage", label: "Spillage" }
                    ].map((filter) => (
                      <Badge
                        key={filter.key}
                        variant={complaintsTypeFilter === filter.key ? "default" : "outline"}
                        className={`cursor-pointer ${complaintsTypeFilter === filter.key ? "" : "hover:bg-muted"}`}
                        onClick={() => { setComplaintsTypeFilter(filter.key); setComplaintsPage(1); }}
                      >
                        {filter.label}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              {(() => {
                const filteredData = complaintsData.filter(row => {
                  const statusMatch = complaintsStatusFilter === "all" || row.status === complaintsStatusFilter;
                  const typeMatch = complaintsTypeFilter === "all" || row.type === complaintsTypeFilter;
                  return statusMatch && typeMatch;
                });
                
                return (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <Card className="bg-primary/10 border-primary/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-primary">{filteredData.length}</p>
                          <p className="text-xs text-muted-foreground">Total Complaints</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-green-500/10 border-green-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-green-600">{filteredData.filter(d => d.status === "resolved").length}</p>
                          <p className="text-xs text-muted-foreground">Resolved</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-yellow-500/10 border-yellow-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-yellow-600">{filteredData.filter(d => d.status === "in-progress").length}</p>
                          <p className="text-xs text-muted-foreground">In Progress</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-red-500/10 border-red-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-red-600">{filteredData.filter(d => d.status === "pending").length}</p>
                          <p className="text-xs text-muted-foreground">Pending</p>
                        </CardContent>
                      </Card>
                    </div>

                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-muted/50">
                            <TableHead>ID</TableHead>
                            <TableHead>Date</TableHead>
                            <TableHead>Ward</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead>Truck</TableHead>
                            <TableHead className="text-center">Response Time</TableHead>
                            <TableHead>Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {paginate(filteredData, complaintsPage).map((row) => (
                            <TableRow key={row.id}>
                              <TableCell className="font-mono text-xs font-medium">{row.id}</TableCell>
                              <TableCell>{row.date}</TableCell>
                              <TableCell>{row.ward}</TableCell>
                              <TableCell>
                                <Badge variant="outline">{row.type}</Badge>
                              </TableCell>
                              <TableCell className="font-mono text-xs">{row.truck}</TableCell>
                              <TableCell className="text-center">{row.responseTime}</TableCell>
                              <TableCell>
                                <Badge 
                                  className={
                                    row.status === "resolved" 
                                      ? "bg-green-500/20 text-green-700 border-green-500/30" 
                                      : row.status === "in-progress" 
                                      ? "bg-yellow-500/20 text-yellow-700 border-yellow-500/30"
                                      : "bg-red-500/20 text-red-700 border-red-500/30"
                                  }
                                >
                                  {row.status}
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    {renderPagination(complaintsPage, filteredData.length, setComplaintsPage)}
                  </>
                );
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Dump Yard Log Report */}
        <TabsContent value="dumpyard" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Scale className="h-5 w-5 text-primary" />
                  Dump Yard & GTP Log Report
                </CardTitle>
                <CardDescription>Entry counts, weight per trip, and site capacity utilization</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("dumpyard_log", "excel")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> Excel</Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("dumpyard_log", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Dump Yard")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="bg-primary/10 border-primary/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-primary">123</p>
                    <p className="text-xs text-muted-foreground">Total Entries</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-500/10 border-blue-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-blue-600">561.7 T</p>
                    <p className="text-xs text-muted-foreground">Total Weight</p>
                  </CardContent>
                </Card>
                <Card className="bg-green-500/10 border-green-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">4.57 T</p>
                    <p className="text-xs text-muted-foreground">Avg per Entry</p>
                  </CardContent>
                </Card>
                <Card className="bg-orange-500/10 border-orange-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-orange-600">56.5%</p>
                    <p className="text-xs text-muted-foreground">Avg Capacity</p>
                  </CardContent>
                </Card>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div className="h-64">
                  <p className="text-sm font-medium mb-2 text-muted-foreground">Zone-wise Distribution</p>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={zoneWiseData}
                        cx="50%"
                        cy="50%"
                        innerRadius={40}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        {zoneWiseData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead>Site</TableHead>
                        <TableHead className="text-center">Entries</TableHead>
                        <TableHead className="text-center">Total (T)</TableHead>
                        <TableHead className="text-center">Avg (T)</TableHead>
                        <TableHead>Capacity</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {dumpYardData.map((row, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{row.site}</TableCell>
                          <TableCell className="text-center">{row.entries}</TableCell>
                          <TableCell className="text-center">{row.totalWeight}</TableCell>
                          <TableCell className="text-center">{row.avgWeight}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={row.capacity} className="h-2 w-16" />
                              <span className={`text-xs ${row.capacity >= 70 ? "text-orange-600" : "text-green-600"}`}>
                                {row.capacity}%
                              </span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Expiry Report */}
        <TabsContent value="expiry" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-primary" />
                  Insurance & License Expiry Report
                </CardTitle>
                <CardDescription>Track truck insurance, fitness certificates, and driver license expiration dates</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("expiry_report", "excel")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> Excel</Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("expiry_report", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Expiry Report")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
                <Button variant="outline" size="sm" onClick={() => handlePrint("expiry_report")}>
                  <Printer className="h-4 w-4 mr-1" /> Print
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Summary Cards */}
              {(() => {
                const today = new Date();
                const truckInsuranceExpiring = trucks.filter((t) => {
                  const insuranceDate = getTruckInsuranceDate(t);
                  const insuranceParsed = safeParseISO(insuranceDate);
                  if (!insuranceParsed) return false;
                  const days = differenceInDays(insuranceParsed, today);
                  return days >= 0 && days <= 30;
                }).length;
                const truckInsuranceExpired = trucks.filter((t) => {
                  const insuranceDate = getTruckInsuranceDate(t);
                  const insuranceParsed = safeParseISO(insuranceDate);
                  if (!insuranceParsed) return false;
                  return differenceInDays(insuranceParsed, today) < 0;
                }).length;
                const truckFitnessExpiring = trucks.filter((t) => {
                  const fitnessDate = getTruckFitnessDate(t);
                  const fitnessParsed = safeParseISO(fitnessDate);
                  if (!fitnessParsed) return false;
                  const days = differenceInDays(fitnessParsed, today);
                  return days >= 0 && days <= 30;
                }).length;
                const truckFitnessExpired = trucks.filter((t) => {
                  const fitnessDate = getTruckFitnessDate(t);
                  const fitnessParsed = safeParseISO(fitnessDate);
                  if (!fitnessParsed) return false;
                  return differenceInDays(fitnessParsed, today) < 0;
                }).length;
                const driverLicenseExpiring = drivers.filter((d) => {
                  const licenseDate = getDriverLicenseDate(d);
                  const licenseParsed = safeParseISO(licenseDate);
                  if (!licenseParsed) return false;
                  const days = differenceInDays(licenseParsed, today);
                  return days >= 0 && days <= 30;
                }).length;
                const driverLicenseExpired = drivers.filter((d) => {
                  const licenseDate = getDriverLicenseDate(d);
                  const licenseParsed = safeParseISO(licenseDate);
                  if (!licenseParsed) return false;
                  return differenceInDays(licenseParsed, today) < 0;
                }).length;

                return (
                  <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                    <Card className="bg-red-500/10 border-red-500/20">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-red-600">{truckInsuranceExpired}</p>
                        <p className="text-xs text-muted-foreground">Insurance Expired</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-orange-500/10 border-orange-500/20">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-orange-600">{truckInsuranceExpiring}</p>
                        <p className="text-xs text-muted-foreground">Insurance Expiring</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-red-500/10 border-red-500/20">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-red-600">{truckFitnessExpired}</p>
                        <p className="text-xs text-muted-foreground">Fitness Expired</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-orange-500/10 border-orange-500/20">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-orange-600">{truckFitnessExpiring}</p>
                        <p className="text-xs text-muted-foreground">Fitness Expiring</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-red-500/10 border-red-500/20">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-red-600">{driverLicenseExpired}</p>
                        <p className="text-xs text-muted-foreground">License Expired</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-orange-500/10 border-orange-500/20">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-orange-600">{driverLicenseExpiring}</p>
                        <p className="text-xs text-muted-foreground">License Expiring</p>
                      </CardContent>
                    </Card>
                  </div>
                );
              })()}

              {/* Truck Insurance & Fitness Table */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Truck className="h-5 w-5 text-primary" />
                    Truck Insurance & Fitness Expiry
                  </h3>
                  <Badge variant="outline" className="text-xs">
                    {trucks.length} Trucks
                  </Badge>
                </div>
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead>Vehicle No.</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Vendor</TableHead>
                        <TableHead>Insurance Expiry</TableHead>
                        <TableHead>Insurance Status</TableHead>
                        <TableHead>Fitness Expiry</TableHead>
                        <TableHead>Fitness Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {paginate(trucks, expiryTruckPage).map((truck) => {
                        const today = new Date();
                        const insuranceDate = getTruckInsuranceDate(truck);
                        const fitnessDate = getTruckFitnessDate(truck);
                        const insuranceParsed = safeParseISO(insuranceDate);
                        const fitnessParsed = safeParseISO(fitnessDate);
                        const insuranceDays = insuranceParsed ? differenceInDays(insuranceParsed, today) : null;
                        const fitnessDays = fitnessParsed ? differenceInDays(fitnessParsed, today) : null;
                        
                        const getStatusBadge = (days: number | null) => {
                          if (days === null) return <Badge variant="secondary">Unknown</Badge>;
                          if (days < 0) return <Badge variant="destructive">Expired</Badge>;
                          if (days <= 7) return <Badge className="bg-orange-500 text-white">Critical ({days}d)</Badge>;
                          if (days <= 30) return <Badge variant="secondary" className="bg-yellow-500/20 text-yellow-700">Warning ({days}d)</Badge>;
                          return <Badge variant="secondary" className="bg-green-500/20 text-green-700">Valid ({days}d)</Badge>;
                        };

                        return (
                          <TableRow key={truck.id}>
                            <TableCell className="font-mono font-medium">{truck.registrationNumber ?? truck.registration_number ?? truck.id}</TableCell>
                            <TableCell className="capitalize">{(truck.type || "").replace('-', ' ')}</TableCell>
                            <TableCell>{truck.vendorId ?? truck.vendor_id ?? "-"}</TableCell>
                            <TableCell>{insuranceParsed ? format(insuranceParsed, 'dd MMM yyyy') : "N/A"}</TableCell>
                            <TableCell>{getStatusBadge(insuranceDays)}</TableCell>
                            <TableCell>{fitnessParsed ? format(fitnessParsed, 'dd MMM yyyy') : "N/A"}</TableCell>
                            <TableCell>{getStatusBadge(fitnessDays)}</TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
                {renderPagination(expiryTruckPage, trucks.length, setExpiryTruckPage)}
              </div>

              {/* Driver License Table */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <IdCard className="h-5 w-5 text-primary" />
                    Driver License Expiry
                  </h3>
                  <Badge variant="outline" className="text-xs">
                    {drivers.length} Drivers
                  </Badge>
                </div>
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead>Driver ID</TableHead>
                        <TableHead>Name</TableHead>
                        <TableHead>Phone</TableHead>
                        <TableHead>License Number</TableHead>
                        <TableHead>License Expiry</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Days Left</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {paginate(drivers, expiryDriverPage).map((driver) => {
                        const today = new Date();
                        const licenseDate = getDriverLicenseDate(driver);
                        const licenseParsed = safeParseISO(licenseDate);
                        const licenseDays = licenseParsed ? differenceInDays(licenseParsed, today) : null;
                        
                        const getStatusBadge = (days: number | null) => {
                          if (days === null) return <Badge variant="secondary">Unknown</Badge>;
                          if (days < 0) return <Badge variant="destructive">Expired</Badge>;
                          if (days <= 7) return <Badge className="bg-orange-500 text-white">Critical</Badge>;
                          if (days <= 30) return <Badge variant="secondary" className="bg-yellow-500/20 text-yellow-700">Warning</Badge>;
                          return <Badge variant="secondary" className="bg-green-500/20 text-green-700">Valid</Badge>;
                        };

                        return (
                          <TableRow key={driver.id}>
                            <TableCell className="font-mono">{driver.id}</TableCell>
                            <TableCell className="font-medium">{driver.name}</TableCell>
                            <TableCell>{driver.phone}</TableCell>
                            <TableCell className="font-mono text-xs">{driver.licenseNumber ?? driver.license_number ?? "-"}</TableCell>
                            <TableCell>{licenseParsed ? format(licenseParsed, 'dd MMM yyyy') : "N/A"}</TableCell>
                            <TableCell>{getStatusBadge(licenseDays)}</TableCell>
                            <TableCell className={`font-medium ${licenseDays === null ? 'text-muted-foreground' : licenseDays < 0 ? 'text-red-600' : licenseDays <= 7 ? 'text-orange-600' : licenseDays <= 30 ? 'text-yellow-600' : 'text-green-600'}`}>
                              {licenseDays === null ? "N/A" : licenseDays < 0 ? `${Math.abs(licenseDays)} days ago` : `${licenseDays} days`}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
                {renderPagination(expiryDriverPage, drivers.length, setExpiryDriverPage)}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Spare Truck Usage Report */}
        <TabsContent value="spare-usage" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <ArrowRightLeft className="h-5 w-5 text-primary" />
                  Spare Truck Usage Report
                </CardTitle>
                <CardDescription>Track spare truck deployments and breakdown replacements</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("spare_usage", "excel")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> Excel</Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("spare_usage", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Spare Usage")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Status:</span>
                <div className="flex gap-1">
                  {[
                    { key: "all", label: "All" },
                    { key: "active", label: "Active" },
                    { key: "completed", label: "Completed" }
                  ].map((filter) => (
                    <Badge
                      key={filter.key}
                      variant={spareStatusFilter === filter.key ? "default" : "outline"}
                      className={`cursor-pointer ${spareStatusFilter === filter.key ? "" : "hover:bg-muted"}`}
                      onClick={() => { setSpareStatusFilter(filter.key); setSpareUsagePage(1); }}
                    >
                      {filter.label}
                    </Badge>
                  ))}
                </div>
              </div>

              {(() => {
                const filteredData = spareStatusFilter === "all" 
                  ? spareUsageData 
                  : spareUsageData.filter(d => d.status === spareStatusFilter);
                  
                return (
                  <>
                    {/* Summary Cards */}
                    <div className="grid gap-4 md:grid-cols-4">
                      <Card className="bg-primary/10 border-primary/30">
                        <CardContent className="pt-4">
                          <div className="text-2xl font-bold text-primary">{filteredData.length}</div>
                          <p className="text-sm text-muted-foreground">Total Deployments</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-green-500/10 border-green-500/30">
                        <CardContent className="pt-4">
                          <div className="text-2xl font-bold text-green-600">{filteredData.filter(s => s.status === "completed").length}</div>
                          <p className="text-sm text-muted-foreground">Completed</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-yellow-500/10 border-yellow-500/30">
                        <CardContent className="pt-4">
                          <div className="text-2xl font-bold text-yellow-600">{filteredData.filter(s => s.status === "active").length}</div>
                          <p className="text-sm text-muted-foreground">Currently Active</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-muted">
                        <CardContent className="pt-4">
                          <div className="text-2xl font-bold">~5.5h</div>
                          <p className="text-sm text-muted-foreground">Avg Duration</p>
                        </CardContent>
                      </Card>
                    </div>

                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-muted/50">
                            <TableHead>Date</TableHead>
                            <TableHead>Spare Truck</TableHead>
                            <TableHead>Original Truck</TableHead>
                            <TableHead>Route</TableHead>
                            <TableHead>Vendor</TableHead>
                            <TableHead>Breakdown Reason</TableHead>
                            <TableHead>Activated</TableHead>
                            <TableHead>Duration</TableHead>
                            <TableHead>Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {paginate(filteredData, spareUsagePage).map((record) => (
                            <TableRow key={record.id}>
                              <TableCell>{record.date}</TableCell>
                              <TableCell className="font-medium">
                                <div className="flex items-center gap-2">
                                  <Badge className="bg-primary/20 text-primary border-primary/30 text-xs">SPARE</Badge>
                                  {record.spareTruck}
                                </div>
                              </TableCell>
                              <TableCell>{record.originalTruck}</TableCell>
                              <TableCell>{record.route}</TableCell>
                              <TableCell className="text-sm">{record.vendor}</TableCell>
                              <TableCell>
                                <div className="flex items-center gap-1">
                                  <Wrench className="h-3 w-3 text-muted-foreground" />
                                  {record.breakdownReason}
                                </div>
                              </TableCell>
                              <TableCell>{record.activatedAt}</TableCell>
                              <TableCell className="font-medium">{record.duration}</TableCell>
                              <TableCell>
                                {record.status === "active" ? (
                                  <Badge className="bg-yellow-500/20 text-yellow-700">Active</Badge>
                                ) : (
                                  <Badge className="bg-green-500/20 text-green-700">Completed</Badge>
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    {renderPagination(spareUsagePage, filteredData.length, setSpareUsagePage)}
                  </>
                );
              })()}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

