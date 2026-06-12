import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format, subDays } from "date-fns";
import {
  Building2,
  CheckCircle2,
  Clock,
  FileSpreadsheet,
  MapPin,
  PackageCheck,
  RefreshCw,
  Route,
  Scale,
  Search,
  Truck,
} from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { apiService } from "@/services/api";

const today = () => format(new Date(), "yyyy-MM-dd");
const sevenDaysAgo = () => format(subDays(new Date(), 7), "yyyy-MM-dd");
const toDatetimeLocal = (value = new Date()) => {
  const offsetMs = value.getTimezoneOffset() * 60 * 1000;
  return new Date(value.getTime() - offsetMs).toISOString().slice(0, 16);
};

const emptyForm = () => ({
  vehicle_id: "",
  gts_pickup_point_id: "",
  dump_yard_id: "",
  material_type: "",
  service_date: today(),
  entry_time: toDatetimeLocal(),
  gross_weight_kg: "",
  tare_weight_kg: "",
  net_weight_kg: "",
  slip_number: "",
  operator_name: "",
  remarks: "",
});

const fieldValue = (value: unknown, fallback = "-") => {
  const normalized = value == null ? "" : String(value).trim();
  return normalized || fallback;
};

const excelEscape = (value: unknown) =>
  String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const excelCell = (value: unknown, style = "Cell", type: "String" | "Number" = "String", mergeAcross = 0) =>
  `<Cell ss:StyleID="${style}"${mergeAcross ? ` ss:MergeAcross="${mergeAcross}"` : ""}><Data ss:Type="${type}">${excelEscape(value)}</Data></Cell>`;

const excelRow = (cells: string[], height?: number) =>
  `<Row${height ? ` ss:Height="${height}"` : ""}>${cells.join("")}</Row>`;

const textEncoder = new TextEncoder();

const crcTable = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i += 1) {
    let c = i;
    for (let k = 0; k < 8; k += 1) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[i] = c >>> 0;
  }
  return table;
})();

const crc32 = (bytes: Uint8Array) => {
  let crc = 0xffffffff;
  for (let i = 0; i < bytes.length; i += 1) {
    crc = crcTable[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
};

const writeUint16 = (target: number[], value: number) => {
  target.push(value & 0xff, (value >>> 8) & 0xff);
};

const writeUint32 = (target: number[], value: number) => {
  target.push(value & 0xff, (value >>> 8) & 0xff, (value >>> 16) & 0xff, (value >>> 24) & 0xff);
};

const concatBytes = (parts: Uint8Array[]) => {
  const total = parts.reduce((sum, part) => sum + part.length, 0);
  const output = new Uint8Array(total);
  let offset = 0;
  parts.forEach((part) => {
    output.set(part, offset);
    offset += part.length;
  });
  return output;
};

const createZip = (files: Array<{ path: string; content: string }>) => {
  const localParts: Uint8Array[] = [];
  const centralParts: Uint8Array[] = [];
  let offset = 0;
  const now = new Date();
  const dosTime = (now.getHours() << 11) | (now.getMinutes() << 5) | Math.floor(now.getSeconds() / 2);
  const dosDate = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();

  files.forEach((file) => {
    const nameBytes = textEncoder.encode(file.path);
    const contentBytes = textEncoder.encode(file.content);
    const crc = crc32(contentBytes);
    const localHeader: number[] = [];
    writeUint32(localHeader, 0x04034b50);
    writeUint16(localHeader, 20);
    writeUint16(localHeader, 0);
    writeUint16(localHeader, 0);
    writeUint16(localHeader, dosTime);
    writeUint16(localHeader, dosDate);
    writeUint32(localHeader, crc);
    writeUint32(localHeader, contentBytes.length);
    writeUint32(localHeader, contentBytes.length);
    writeUint16(localHeader, nameBytes.length);
    writeUint16(localHeader, 0);
    const local = concatBytes([new Uint8Array(localHeader), nameBytes, contentBytes]);
    localParts.push(local);

    const centralHeader: number[] = [];
    writeUint32(centralHeader, 0x02014b50);
    writeUint16(centralHeader, 20);
    writeUint16(centralHeader, 20);
    writeUint16(centralHeader, 0);
    writeUint16(centralHeader, 0);
    writeUint16(centralHeader, dosTime);
    writeUint16(centralHeader, dosDate);
    writeUint32(centralHeader, crc);
    writeUint32(centralHeader, contentBytes.length);
    writeUint32(centralHeader, contentBytes.length);
    writeUint16(centralHeader, nameBytes.length);
    writeUint16(centralHeader, 0);
    writeUint16(centralHeader, 0);
    writeUint16(centralHeader, 0);
    writeUint16(centralHeader, 0);
    writeUint32(centralHeader, 0);
    writeUint32(centralHeader, offset);
    centralParts.push(concatBytes([new Uint8Array(centralHeader), nameBytes]));
    offset += local.length;
  });

  const centralDirectory = concatBytes(centralParts);
  const end: number[] = [];
  writeUint32(end, 0x06054b50);
  writeUint16(end, 0);
  writeUint16(end, 0);
  writeUint16(end, files.length);
  writeUint16(end, files.length);
  writeUint32(end, centralDirectory.length);
  writeUint32(end, offset);
  writeUint16(end, 0);
  return concatBytes([...localParts, centralDirectory, new Uint8Array(end)]);
};

const columnName = (index: number) => {
  let name = "";
  let value = index + 1;
  while (value > 0) {
    const remainder = (value - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    value = Math.floor((value - 1) / 26);
  }
  return name;
};

const xlsxCell = (value: unknown, row: number, col: number, style = 1, type: "s" | "n" = "s") => {
  const ref = `${columnName(col)}${row}`;
  if (type === "n") {
    const numeric = Number(value);
    return `<c r="${ref}" s="${style}"><v>${Number.isFinite(numeric) ? numeric : 0}</v></c>`;
  }
  return `<c r="${ref}" s="${style}" t="inlineStr"><is><t>${excelEscape(value)}</t></is></c>`;
};

const xlsxRow = (rowIndex: number, values: Array<{ value: unknown; style?: number; type?: "s" | "n" }>, height?: number) =>
  `<row r="${rowIndex}"${height ? ` ht="${height}" customHeight="1"` : ""}>${values
    .map((cell, colIndex) => xlsxCell(cell.value, rowIndex, colIndex, cell.style ?? 1, cell.type ?? "s"))
    .join("")}</row>`;

const xlsxWorksheet = (
  rows: string[],
  options?: {
    cols?: number[];
    merges?: string[];
    freezeRow?: number;
  }
) => {
  const cols = options?.cols?.length
    ? `<cols>${options.cols.map((width, index) => `<col min="${index + 1}" max="${index + 1}" width="${width}" customWidth="1"/>`).join("")}</cols>`
    : "";
  const merges = options?.merges?.length ? `<mergeCells count="${options.merges.length}">${options.merges.map((ref) => `<mergeCell ref="${ref}"/>`).join("")}</mergeCells>` : "";
  const pane = options?.freezeRow
    ? `<sheetViews><sheetView workbookViewId="0"><pane ySplit="${options.freezeRow}" topLeftCell="A${options.freezeRow + 1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>`
    : `<sheetViews><sheetView workbookViewId="0"/></sheetViews>`;
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">${pane}${cols}<sheetData>${rows.join("")}</sheetData>${merges}</worksheet>`;
};

const normalizedDate = (row: any) => String(row.service_date || row.date || "").slice(0, 10) || "-";
const normalizedMaterialLabel = (row: any) => fieldValue(row.material_label || row.material || row.material_type);

const groupSum = (rows: any[], keyFn: (row: any) => string) => {
  const map = new Map<string, { key: string; count: number; net: number; gross: number; tare: number }>();
  rows.forEach((row) => {
    const key = keyFn(row);
    const current = map.get(key) || { key, count: 0, net: 0, gross: 0, tare: 0 };
    current.count += 1;
    current.net += Number(row.net_weight_kg ?? row.netWeightKg ?? 0) || 0;
    current.gross += Number(row.gross_weight_kg ?? row.grossWeightKg ?? 0) || 0;
    current.tare += Number(row.tare_weight_kg ?? row.tareWeightKg ?? 0) || 0;
    map.set(key, current);
  });
  return Array.from(map.values()).sort((a, b) => b.net - a.net);
};

const buildWeighmentWorkbook = (rows: any[], periodFrom: string, periodTo: string) => {
  const generatedAt = format(new Date(), "dd MMM yyyy, HH:mm");
  const sortedRows = [...rows].sort((a, b) => String(a.entry_time || "").localeCompare(String(b.entry_time || "")));
  const totalNet = sortedRows.reduce((sum, row) => sum + (Number(row.net_weight_kg ?? row.netWeightKg ?? 0) || 0), 0);
  const totalGross = sortedRows.reduce((sum, row) => sum + (Number(row.gross_weight_kg ?? row.grossWeightKg ?? 0) || 0), 0);
  const totalTare = sortedRows.reduce((sum, row) => sum + (Number(row.tare_weight_kg ?? row.tareWeightKg ?? 0) || 0), 0);
  const uniqueTrucks = new Set(sortedRows.map((row) => row.vehicle_number || row.registration_number || row.vehicle_id).filter(Boolean)).size;
  const uniqueMaterials = new Set(sortedRows.map((row) => row.material_type || row.material_label).filter(Boolean)).size;
  const avgNet = sortedRows.length ? totalNet / sortedRows.length : 0;
  const materialRows = groupSum(sortedRows, normalizedMaterialLabel);
  const dayRows = groupSum(sortedRows, normalizedDate).sort((a, b) => a.key.localeCompare(b.key));
  const vehicleRows = groupSum(sortedRows, (row) => fieldValue(row.vehicle_number || row.registration_number || row.vehicle_id));
  const maxMaterialNet = Math.max(...materialRows.map((row) => row.net), 1);
  const maxDailyNet = Math.max(...dayRows.map((row) => row.net), 1);

  const kpiRows = [
    ["Total Entries", sortedRows.length, "records"],
    ["Net Collection", totalNet / 1000, "tons"],
    ["Gross Weight", totalGross / 1000, "tons"],
    ["Tare Weight", totalTare / 1000, "tons"],
    ["Average Net / Entry", avgNet, "kg"],
    ["Active Trucks", uniqueTrucks, "trucks"],
    ["Material Types", uniqueMaterials, "types"],
  ];

  const summarySheet = `
  <Worksheet ss:Name="Executive Summary">
    <Table ss:ExpandedColumnCount="8" ss:ExpandedRowCount="${20 + kpiRows.length}" x:FullColumns="1" x:FullRows="1">
      <Column ss:Width="24"/><Column ss:Width="190"/><Column ss:Width="120"/><Column ss:Width="100"/><Column ss:Width="120"/><Column ss:Width="120"/><Column ss:Width="120"/><Column ss:Width="120"/>
      ${excelRow([excelCell("SMART CITY SOLID WASTE MANAGEMENT", "ReportEyebrow", "String", 7)], 24)}
      ${excelRow([excelCell("Dump Yard Weighment Report", "ReportTitle", "String", 7)], 34)}
      ${excelRow([excelCell(`Period: ${periodFrom} to ${periodTo} | Generated: ${generatedAt}`, "ReportMeta", "String", 7)], 22)}
      ${excelRow([excelCell("", "Blank", "String", 7)], 8)}
      ${excelRow([excelCell("KPI", "Header"), excelCell("Value", "Header"), excelCell("Unit", "Header"), excelCell("Operational Reading", "Header", "String", 4)], 24)}
      ${kpiRows
        .map(([label, value, unit], index) =>
          excelRow([
            excelCell(label, index % 2 ? "KpiLabelAlt" : "KpiLabel"),
            excelCell(typeof value === "number" ? Number(value).toFixed(unit === "records" || unit === "trucks" || unit === "types" ? 0 : unit === "tons" ? 3 : 1) : value, "KpiValue", "Number"),
            excelCell(unit, "KpiUnit"),
            excelCell(index === 0 ? "Use this report for dump yard reconciliation, material analytics, and route-wise tonnage review." : "", index === 0 ? "Narrative" : "Blank", "String", 4),
          ], 24)
        )
        .join("")}
      ${excelRow([excelCell("", "Blank", "String", 7)], 8)}
      ${excelRow([excelCell("Top Material Mix", "Section", "String", 7)], 26)}
      ${excelRow([excelCell("Material", "Header"), excelCell("Entries", "Header"), excelCell("Net KG", "Header"), excelCell("Net Ton", "Header"), excelCell("Share", "Header"), excelCell("Visual", "Header", "String", 3)], 24)}
      ${materialRows.slice(0, 8).map((row) => {
        const pct = totalNet > 0 ? (row.net / totalNet) * 100 : 0;
        const blocks = Math.max(1, Math.round((row.net / maxMaterialNet) * 28));
        return excelRow([
          excelCell(row.key, "CellStrong"),
          excelCell(row.count, "CellCenter", "Number"),
          excelCell(row.net.toFixed(1), "CellRight", "Number"),
          excelCell((row.net / 1000).toFixed(3), "CellRight", "Number"),
          excelCell(`${pct.toFixed(1)}%`, "CellCenter"),
          excelCell("█".repeat(blocks), "BarCell", "String", 3),
        ], 24);
      }).join("")}
    </Table>
    <WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel"><FreezePanes/><FrozenNoSplit/><SplitHorizontal>5</SplitHorizontal><TopRowBottomPane>5</TopRowBottomPane></WorksheetOptions>
  </Worksheet>`;

  const trendSheet = `
  <Worksheet ss:Name="Daily Trend Chart">
    <Table ss:ExpandedColumnCount="8" ss:ExpandedRowCount="${12 + dayRows.length}" x:FullColumns="1" x:FullRows="1">
      <Column ss:Width="130"/><Column ss:Width="90"/><Column ss:Width="110"/><Column ss:Width="110"/><Column ss:Width="110"/><Column ss:Width="300"/><Column ss:Width="90"/><Column ss:Width="90"/>
      ${excelRow([excelCell("Seven Day Collection Trend", "ReportTitle", "String", 7)], 32)}
      ${excelRow([excelCell("Visual bar length is proportional to daily net collection.", "ReportMeta", "String", 7)], 22)}
      ${excelRow([excelCell("Date", "Header"), excelCell("Entries", "Header"), excelCell("Gross KG", "Header"), excelCell("Tare KG", "Header"), excelCell("Net KG", "Header"), excelCell("Trend Bar", "Header"), excelCell("Net Ton", "Header"), excelCell("Avg KG", "Header")], 24)}
      ${dayRows.map((row) => {
        const blocks = Math.max(1, Math.round((row.net / maxDailyNet) * 34));
        return excelRow([
          excelCell(row.key, "CellStrong"),
          excelCell(row.count, "CellCenter", "Number"),
          excelCell(row.gross.toFixed(1), "CellRight", "Number"),
          excelCell(row.tare.toFixed(1), "CellRight", "Number"),
          excelCell(row.net.toFixed(1), "CellRight", "Number"),
          excelCell("█".repeat(blocks), "TrendBar"),
          excelCell((row.net / 1000).toFixed(3), "CellRight", "Number"),
          excelCell((row.net / Math.max(row.count, 1)).toFixed(1), "CellRight", "Number"),
        ], 24);
      }).join("")}
    </Table>
  </Worksheet>`;

  const vehicleSheet = `
  <Worksheet ss:Name="Vehicle Summary">
    <Table ss:ExpandedColumnCount="6" ss:ExpandedRowCount="${8 + vehicleRows.length}" x:FullColumns="1" x:FullRows="1">
      <Column ss:Width="150"/><Column ss:Width="90"/><Column ss:Width="120"/><Column ss:Width="120"/><Column ss:Width="120"/><Column ss:Width="140"/>
      ${excelRow([excelCell("Vehicle Wise Dump Yard Weighment", "ReportTitle", "String", 5)], 32)}
      ${excelRow([excelCell("Truck", "Header"), excelCell("Entries", "Header"), excelCell("Gross KG", "Header"), excelCell("Tare KG", "Header"), excelCell("Net KG", "Header"), excelCell("Net Ton", "Header")], 24)}
      ${vehicleRows.map((row) => excelRow([
        excelCell(row.key, "CellStrong"),
        excelCell(row.count, "CellCenter", "Number"),
        excelCell(row.gross.toFixed(1), "CellRight", "Number"),
        excelCell(row.tare.toFixed(1), "CellRight", "Number"),
        excelCell(row.net.toFixed(1), "CellRight", "Number"),
        excelCell((row.net / 1000).toFixed(3), "CellRight", "Number"),
      ], 24)).join("")}
    </Table>
  </Worksheet>`;

  const detailsSheet = `
  <Worksheet ss:Name="Detail Records">
    <Table ss:ExpandedColumnCount="16" ss:ExpandedRowCount="${8 + sortedRows.length}" x:FullColumns="1" x:FullRows="1">
      <Column ss:Width="95"/><Column ss:Width="120"/><Column ss:Width="120"/><Column ss:Width="100"/><Column ss:Width="100"/><Column ss:Width="100"/><Column ss:Width="100"/><Column ss:Width="150"/><Column ss:Width="150"/><Column ss:Width="130"/><Column ss:Width="120"/><Column ss:Width="100"/><Column ss:Width="100"/><Column ss:Width="100"/><Column ss:Width="120"/><Column ss:Width="220"/>
      ${excelRow([excelCell("Detailed Weighment Register", "ReportTitle", "String", 15)], 32)}
      ${excelRow([
        "Date", "Entry Time", "Vehicle", "Registration", "Zone", "Ward", "Route", "GTS", "Dump Yard", "Material", "Gross KG", "Tare KG", "Net KG", "Net Ton", "Slip Number", "Remarks"
      ].map((header) => excelCell(header, "Header")), 24)}
      ${sortedRows.map((row, index) => excelRow([
        excelCell(normalizedDate(row), index % 2 ? "CellAlt" : "Cell"),
        excelCell(row.entry_time ? format(new Date(row.entry_time), "dd MMM yyyy HH:mm") : "-", index % 2 ? "CellAlt" : "Cell"),
        excelCell(fieldValue(row.vehicle_number), index % 2 ? "CellStrongAlt" : "CellStrong"),
        excelCell(fieldValue(row.registration_number), index % 2 ? "CellAlt" : "Cell"),
        excelCell(fieldValue(row.zone_name), index % 2 ? "CellAlt" : "Cell"),
        excelCell(fieldValue(row.ward_name), index % 2 ? "CellAlt" : "Cell"),
        excelCell(fieldValue(row.route_name), index % 2 ? "CellAlt" : "Cell"),
        excelCell(fieldValue(row.gts_name), index % 2 ? "CellAlt" : "Cell"),
        excelCell(fieldValue(row.dump_yard_name), index % 2 ? "CellAlt" : "Cell"),
        excelCell(normalizedMaterialLabel(row), index % 2 ? "CellAlt" : "Cell"),
        excelCell((Number(row.gross_weight_kg || 0)).toFixed(1), "CellRight", "Number"),
        excelCell((Number(row.tare_weight_kg || 0)).toFixed(1), "CellRight", "Number"),
        excelCell((Number(row.net_weight_kg || 0)).toFixed(1), "CellRight", "Number"),
        excelCell((Number(row.net_weight_kg || 0) / 1000).toFixed(3), "CellRight", "Number"),
        excelCell(fieldValue(row.slip_number), index % 2 ? "CellAlt" : "Cell"),
        excelCell(fieldValue(row.remarks), index % 2 ? "CellAlt" : "Cell"),
      ], 22)).join("")}
    </Table>
    <WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel"><FreezePanes/><FrozenNoSplit/><SplitHorizontal>2</SplitHorizontal><TopRowBottomPane>2</TopRowBottomPane></WorksheetOptions>
  </Worksheet>`;

  return `<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:html="http://www.w3.org/TR/REC-html40">
 <DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">
  <Author>SWM Platform</Author>
  <Title>Dump Yard Weighment Report</Title>
  <Created>${new Date().toISOString()}</Created>
 </DocumentProperties>
 <Styles>
  <Style ss:ID="Blank"><Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/></Style>
  <Style ss:ID="ReportEyebrow"><Font ss:FontName="Aptos" ss:Size="9" ss:Bold="1" ss:Color="#0F766E"/><Interior ss:Color="#ECFDF5" ss:Pattern="Solid"/><Alignment ss:Horizontal="Center"/></Style>
  <Style ss:ID="ReportTitle"><Font ss:FontName="Aptos Display" ss:Size="20" ss:Bold="1" ss:Color="#052E2B"/><Interior ss:Color="#D1FAE5" ss:Pattern="Solid"/><Alignment ss:Horizontal="Center" ss:Vertical="Center"/></Style>
  <Style ss:ID="ReportMeta"><Font ss:FontName="Aptos" ss:Size="10" ss:Color="#475569"/><Interior ss:Color="#F8FAFC" ss:Pattern="Solid"/><Alignment ss:Horizontal="Center"/></Style>
  <Style ss:ID="Section"><Font ss:FontName="Aptos" ss:Size="13" ss:Bold="1" ss:Color="#064E3B"/><Interior ss:Color="#A7F3D0" ss:Pattern="Solid"/></Style>
  <Style ss:ID="Header"><Font ss:FontName="Aptos" ss:Size="10" ss:Bold="1" ss:Color="#FFFFFF"/><Interior ss:Color="#0F766E" ss:Pattern="Solid"/><Alignment ss:Horizontal="Center" ss:Vertical="Center"/><Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#064E3B"/></Borders></Style>
  <Style ss:ID="Cell"><Font ss:FontName="Aptos" ss:Size="10" ss:Color="#0F172A"/><Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/><Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/></Borders></Style>
  <Style ss:ID="CellAlt" ss:Parent="Cell"><Interior ss:Color="#F8FAFC" ss:Pattern="Solid"/></Style>
  <Style ss:ID="CellStrong" ss:Parent="Cell"><Font ss:FontName="Aptos" ss:Size="10" ss:Bold="1" ss:Color="#0F172A"/></Style>
  <Style ss:ID="CellStrongAlt" ss:Parent="CellStrong"><Interior ss:Color="#F8FAFC" ss:Pattern="Solid"/></Style>
  <Style ss:ID="CellCenter" ss:Parent="Cell"><Alignment ss:Horizontal="Center"/></Style>
  <Style ss:ID="CellRight" ss:Parent="Cell"><Alignment ss:Horizontal="Right"/></Style>
  <Style ss:ID="KpiLabel"><Font ss:FontName="Aptos" ss:Size="10" ss:Bold="1" ss:Color="#134E4A"/><Interior ss:Color="#ECFDF5" ss:Pattern="Solid"/></Style>
  <Style ss:ID="KpiLabelAlt" ss:Parent="KpiLabel"><Interior ss:Color="#F0FDFA" ss:Pattern="Solid"/></Style>
  <Style ss:ID="KpiValue"><Font ss:FontName="Aptos Display" ss:Size="13" ss:Bold="1" ss:Color="#047857"/><Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/><Alignment ss:Horizontal="Right"/></Style>
  <Style ss:ID="KpiUnit"><Font ss:FontName="Aptos" ss:Size="9" ss:Color="#64748B"/><Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/><Alignment ss:Horizontal="Center"/></Style>
  <Style ss:ID="Narrative"><Font ss:FontName="Aptos" ss:Size="10" ss:Color="#334155"/><Interior ss:Color="#FFFBEB" ss:Pattern="Solid"/></Style>
  <Style ss:ID="BarCell"><Font ss:FontName="Consolas" ss:Size="11" ss:Bold="1" ss:Color="#10B981"/><Interior ss:Color="#F0FDFA" ss:Pattern="Solid"/></Style>
  <Style ss:ID="TrendBar"><Font ss:FontName="Consolas" ss:Size="11" ss:Bold="1" ss:Color="#F59E0B"/><Interior ss:Color="#FFFBEB" ss:Pattern="Solid"/></Style>
 </Styles>
 ${summarySheet}
 ${trendSheet}
 ${vehicleSheet}
 ${detailsSheet}
</Workbook>`;
};

const buildWeighmentXlsx = (rows: any[], periodFrom: string, periodTo: string) => {
  const generatedAt = format(new Date(), "dd MMM yyyy, HH:mm");
  const sortedRows = [...rows].sort((a, b) => String(a.entry_time || "").localeCompare(String(b.entry_time || "")));
  const totalNet = sortedRows.reduce((sum, row) => sum + (Number(row.net_weight_kg ?? row.netWeightKg ?? 0) || 0), 0);
  const totalGross = sortedRows.reduce((sum, row) => sum + (Number(row.gross_weight_kg ?? row.grossWeightKg ?? 0) || 0), 0);
  const totalTare = sortedRows.reduce((sum, row) => sum + (Number(row.tare_weight_kg ?? row.tareWeightKg ?? 0) || 0), 0);
  const uniqueTrucks = new Set(sortedRows.map((row) => row.vehicle_number || row.registration_number || row.vehicle_id).filter(Boolean)).size;
  const uniqueMaterials = new Set(sortedRows.map((row) => row.material_type || row.material_label).filter(Boolean)).size;
  const materialRows = groupSum(sortedRows, normalizedMaterialLabel);
  const dayRows = groupSum(sortedRows, normalizedDate).sort((a, b) => a.key.localeCompare(b.key));
  const vehicleRows = groupSum(sortedRows, (row) => fieldValue(row.vehicle_number || row.registration_number || row.vehicle_id));
  const maxMaterialNet = Math.max(...materialRows.map((row) => row.net), 1);
  const maxDailyNet = Math.max(...dayRows.map((row) => row.net), 1);
  const avgNet = sortedRows.length ? totalNet / sortedRows.length : 0;

  const summaryRows = [
    xlsxRow(1, [{ value: "SMART CITY SOLID WASTE MANAGEMENT", style: 2 }], 24),
    xlsxRow(2, [{ value: "Dump Yard Weighment Report", style: 3 }], 32),
    xlsxRow(3, [{ value: `Period: ${periodFrom} to ${periodTo} | Generated: ${generatedAt}`, style: 4 }], 22),
    xlsxRow(5, [
      { value: "KPI", style: 5 },
      { value: "Value", style: 5 },
      { value: "Unit", style: 5 },
      { value: "Operational Reading", style: 5 },
    ], 24),
    ...[
      ["Total Entries", sortedRows.length, "records"],
      ["Net Collection", Number((totalNet / 1000).toFixed(3)), "tons"],
      ["Gross Weight", Number((totalGross / 1000).toFixed(3)), "tons"],
      ["Tare Weight", Number((totalTare / 1000).toFixed(3)), "tons"],
      ["Average Net / Entry", Number(avgNet.toFixed(1)), "kg"],
      ["Active Trucks", uniqueTrucks, "trucks"],
      ["Material Types", uniqueMaterials, "types"],
    ].map(([label, value, unit], index) =>
      xlsxRow(6 + index, [
        { value: label, style: 6 },
        { value, style: 7, type: "n" },
        { value: unit, style: 8 },
        { value: index === 0 ? "Use this workbook for dump yard reconciliation, material analytics, and route-wise tonnage review." : "", style: index === 0 ? 9 : 1 },
      ], 23)
    ),
    xlsxRow(15, [{ value: "Material Mix Visual", style: 10 }], 26),
    xlsxRow(16, [
      { value: "Material", style: 5 },
      { value: "Entries", style: 5 },
      { value: "Net KG", style: 5 },
      { value: "Net Ton", style: 5 },
      { value: "Share", style: 5 },
      { value: "Visual Bar", style: 5 },
    ], 24),
    ...materialRows.slice(0, 9).map((row, index) => {
      const pct = totalNet > 0 ? (row.net / totalNet) * 100 : 0;
      const blocks = Math.max(1, Math.round((row.net / maxMaterialNet) * 30));
      return xlsxRow(17 + index, [
        { value: row.key, style: 11 },
        { value: row.count, style: 12, type: "n" },
        { value: Number(row.net.toFixed(1)), style: 13, type: "n" },
        { value: Number((row.net / 1000).toFixed(3)), style: 13, type: "n" },
        { value: `${pct.toFixed(1)}%`, style: 12 },
        { value: "█".repeat(blocks), style: 14 },
      ], 23);
    }),
  ];

  const trendRows = [
    xlsxRow(1, [{ value: "Seven Day Collection Trend", style: 3 }], 32),
    xlsxRow(2, [{ value: "Bar length is proportional to daily net collection.", style: 4 }], 22),
    xlsxRow(4, ["Date", "Entries", "Gross KG", "Tare KG", "Net KG", "Trend Bar", "Net Ton", "Avg KG"].map((value) => ({ value, style: 5 })), 24),
    ...dayRows.map((row, index) => {
      const blocks = Math.max(1, Math.round((row.net / maxDailyNet) * 34));
      return xlsxRow(5 + index, [
        { value: row.key, style: 11 },
        { value: row.count, style: 12, type: "n" },
        { value: Number(row.gross.toFixed(1)), style: 13, type: "n" },
        { value: Number(row.tare.toFixed(1)), style: 13, type: "n" },
        { value: Number(row.net.toFixed(1)), style: 13, type: "n" },
        { value: "█".repeat(blocks), style: 15 },
        { value: Number((row.net / 1000).toFixed(3)), style: 13, type: "n" },
        { value: Number((row.net / Math.max(row.count, 1)).toFixed(1)), style: 13, type: "n" },
      ], 23);
    }),
  ];

  const vehicleSummaryRows = [
    xlsxRow(1, [{ value: "Vehicle Wise Dump Yard Weighment", style: 3 }], 32),
    xlsxRow(3, ["Truck", "Entries", "Gross KG", "Tare KG", "Net KG", "Net Ton"].map((value) => ({ value, style: 5 })), 24),
    ...vehicleRows.map((row, index) => xlsxRow(4 + index, [
      { value: row.key, style: 11 },
      { value: row.count, style: 12, type: "n" },
      { value: Number(row.gross.toFixed(1)), style: 13, type: "n" },
      { value: Number(row.tare.toFixed(1)), style: 13, type: "n" },
      { value: Number(row.net.toFixed(1)), style: 13, type: "n" },
      { value: Number((row.net / 1000).toFixed(3)), style: 13, type: "n" },
    ], 23)),
  ];

  const detailHeaders = [
    "Date", "Entry Time", "Vehicle", "Registration", "Zone", "Ward", "Route", "GTS", "Dump Yard", "Material",
    "Gross KG", "Tare KG", "Net KG", "Net Ton", "Slip Number", "Remarks",
  ];
  const detailRows = [
    xlsxRow(1, [{ value: "Detailed Weighment Register", style: 3 }], 32),
    xlsxRow(3, detailHeaders.map((value) => ({ value, style: 5 })), 24),
    ...sortedRows.map((row, index) => xlsxRow(4 + index, [
      { value: normalizedDate(row), style: index % 2 ? 16 : 1 },
      { value: row.entry_time ? format(new Date(row.entry_time), "dd MMM yyyy HH:mm") : "-", style: index % 2 ? 16 : 1 },
      { value: fieldValue(row.vehicle_number), style: index % 2 ? 17 : 11 },
      { value: fieldValue(row.registration_number), style: index % 2 ? 16 : 1 },
      { value: fieldValue(row.zone_name), style: index % 2 ? 16 : 1 },
      { value: fieldValue(row.ward_name), style: index % 2 ? 16 : 1 },
      { value: fieldValue(row.route_name), style: index % 2 ? 16 : 1 },
      { value: fieldValue(row.gts_name), style: index % 2 ? 16 : 1 },
      { value: fieldValue(row.dump_yard_name), style: index % 2 ? 16 : 1 },
      { value: normalizedMaterialLabel(row), style: index % 2 ? 16 : 1 },
      { value: Number(row.gross_weight_kg || 0).toFixed(1), style: 13, type: "n" },
      { value: Number(row.tare_weight_kg || 0).toFixed(1), style: 13, type: "n" },
      { value: Number(row.net_weight_kg || 0).toFixed(1), style: 13, type: "n" },
      { value: (Number(row.net_weight_kg || 0) / 1000).toFixed(3), style: 13, type: "n" },
      { value: fieldValue(row.slip_number), style: index % 2 ? 16 : 1 },
      { value: fieldValue(row.remarks), style: index % 2 ? 16 : 1 },
    ], 22)),
  ];

  const stylesXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="8">
    <font><sz val="10"/><color rgb="FF0F172A"/><name val="Aptos"/></font>
    <font><b/><sz val="9"/><color rgb="FF0F766E"/><name val="Aptos"/></font>
    <font><b/><sz val="20"/><color rgb="FF052E2B"/><name val="Aptos Display"/></font>
    <font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Aptos"/></font>
    <font><b/><sz val="10"/><color rgb="FF134E4A"/><name val="Aptos"/></font>
    <font><b/><sz val="13"/><color rgb="FF047857"/><name val="Aptos Display"/></font>
    <font><b/><sz val="11"/><color rgb="FF10B981"/><name val="Consolas"/></font>
    <font><b/><sz val="11"/><color rgb="FFF59E0B"/><name val="Consolas"/></font>
  </fonts>
  <fills count="9">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFFFFFF"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFECFDF5"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFD1FAE5"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF8FAFC"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF0F766E"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFFFBEB"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF0FDFA"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2"><border/><border><bottom style="thin"><color rgb="FFE2E8F0"/></bottom></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="18">
    <xf numFmtId="0" fontId="0" fillId="2" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="0" fillId="2" borderId="1" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="3" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="2" fillId="4" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="0" fillId="5" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="center"/></xf>
    <xf numFmtId="0" fontId="3" fillId="6" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="4" fillId="3" borderId="1" xfId="0"/>
    <xf numFmtId="4" fontId="5" fillId="2" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="right"/></xf>
    <xf numFmtId="0" fontId="0" fillId="2" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center"/></xf>
    <xf numFmtId="0" fontId="0" fillId="7" borderId="1" xfId="0"/>
    <xf numFmtId="0" fontId="4" fillId="8" borderId="1" xfId="0"/>
    <xf numFmtId="0" fontId="4" fillId="2" borderId="1" xfId="0"/>
    <xf numFmtId="0" fontId="0" fillId="2" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center"/></xf>
    <xf numFmtId="4" fontId="0" fillId="2" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="right"/></xf>
    <xf numFmtId="0" fontId="6" fillId="8" borderId="1" xfId="0"/>
    <xf numFmtId="0" fontId="7" fillId="7" borderId="1" xfId="0"/>
    <xf numFmtId="0" fontId="0" fillId="5" borderId="1" xfId="0"/>
    <xf numFmtId="0" fontId="4" fillId="5" borderId="1" xfId="0"/>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>`;

  const files = [
    {
      path: "[Content_Types].xml",
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet4.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>`,
    },
    {
      path: "_rels/.rels",
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`,
    },
    {
      path: "xl/workbook.xml",
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Executive Summary" sheetId="1" r:id="rId1"/><sheet name="Daily Trend Chart" sheetId="2" r:id="rId2"/><sheet name="Vehicle Summary" sheetId="3" r:id="rId3"/><sheet name="Detail Records" sheetId="4" r:id="rId4"/></sheets></workbook>`,
    },
    {
      path: "xl/_rels/workbook.xml.rels",
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/><Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet4.xml"/><Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`,
    },
    { path: "xl/styles.xml", content: stylesXml },
    {
      path: "xl/worksheets/sheet1.xml",
      content: xlsxWorksheet(summaryRows, { cols: [22, 18, 14, 64, 16, 16], merges: ["A1:F1", "A2:F2", "A3:F3", "A15:F15"], freezeRow: 5 }),
    },
    {
      path: "xl/worksheets/sheet2.xml",
      content: xlsxWorksheet(trendRows, { cols: [18, 12, 15, 15, 15, 42, 14, 14], merges: ["A1:H1", "A2:H2"], freezeRow: 4 }),
    },
    {
      path: "xl/worksheets/sheet3.xml",
      content: xlsxWorksheet(vehicleSummaryRows, { cols: [22, 12, 15, 15, 15, 15], merges: ["A1:F1"], freezeRow: 3 }),
    },
    {
      path: "xl/worksheets/sheet4.xml",
      content: xlsxWorksheet(detailRows, { cols: [13, 21, 18, 18, 14, 14, 14, 25, 25, 18, 14, 14, 14, 14, 18, 40], merges: ["A1:P1"], freezeRow: 3 }),
    },
  ];

  return createZip(files);
};

export default function MasterDumpYardWeighmentEntry() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [truckQuery, setTruckQuery] = useState("");
  const [debouncedTruckQuery, setDebouncedTruckQuery] = useState("");
  const [selectedVehicle, setSelectedVehicle] = useState<any | null>(null);
  const [form, setForm] = useState(emptyForm);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebouncedTruckQuery(truckQuery.trim()), 250);
    return () => window.clearTimeout(handle);
  }, [truckQuery]);

  const { data: truckMatches = [], isFetching: searchingTrucks } = useQuery({
    queryKey: ["vehicles-search", debouncedTruckQuery],
    queryFn: () => apiService.searchVehicles(debouncedTruckQuery, 12),
    enabled: debouncedTruckQuery.length > 0,
    staleTime: 30 * 1000,
  });

  const { data: selectedVehicleDetails, isFetching: loadingVehicleDetails } = useQuery({
    queryKey: ["vehicle-details", selectedVehicle?.id],
    queryFn: () => apiService.getVehicleDetails(String(selectedVehicle.id)),
    enabled: Boolean(selectedVehicle?.id),
  });

  const { data: dumpYards = [] } = useQuery({
    queryKey: ["dump-yards", "weighment-entry"],
    queryFn: () => apiService.getDumpYards({ active: "true" }),
  });

  const { data: materialTypes = [] } = useQuery({
    queryKey: ["secondary-waste-types", "weighment-entry"],
    queryFn: () => apiService.getSecondaryWasteTypes(),
  });

  const { data: history = [], refetch: refetchHistory } = useQuery({
    queryKey: ["dump-yard-weighment", "history", form.service_date],
    queryFn: () =>
      apiService.getDumpYardWeighment({
        date_from: sevenDaysAgo(),
        date_to: today(),
      }),
  });

  useEffect(() => {
    if (!selectedVehicleDetails) return;
    setForm((current) => ({
      ...current,
      vehicle_id: String(selectedVehicleDetails.vehicle_id || selectedVehicleDetails.id || ""),
      gts_pickup_point_id: String(selectedVehicleDetails.gts_pickup_point_id || ""),
      dump_yard_id: String(selectedVehicleDetails.dump_yard_id || current.dump_yard_id || ""),
      material_type: String(selectedVehicleDetails.material_type || current.material_type || "wet_waste"),
    }));
  }, [selectedVehicleDetails]);

  const netWeight = useMemo(() => {
    const gross = Number(form.gross_weight_kg);
    const tare = Number(form.tare_weight_kg);
    if (!Number.isFinite(gross) || !Number.isFinite(tare)) return "";
    return Math.max(gross - tare, 0).toFixed(1);
  }, [form.gross_weight_kg, form.tare_weight_kg]);

  const createMutation = useMutation({
    mutationFn: (payload: any) => apiService.createDumpYardWeighmentEntry(payload),
    onSuccess: () => {
      toast({ title: "Weighment saved", description: "Dump yard entry is now available in reports and dashboards." });
      setForm((current) => ({
        ...emptyForm(),
        vehicle_id: current.vehicle_id,
        gts_pickup_point_id: current.gts_pickup_point_id,
        dump_yard_id: current.dump_yard_id,
        material_type: current.material_type,
        service_date: today(),
      }));
      queryClient.invalidateQueries({ queryKey: ["dump-yard-weighment"] });
      queryClient.invalidateQueries({ queryKey: ["reports-data"] });
      refetchHistory();
    },
    onError: (error: any) => {
      toast({
        title: "Unable to save weighment",
        description: error?.message || "Please verify the truck and weight details.",
        variant: "destructive",
      });
    },
  });

  const selectVehicle = (vehicle: any) => {
    setSelectedVehicle(vehicle);
    setTruckQuery(vehicle.vehicle_number || vehicle.registration_number || "");
    setDebouncedTruckQuery("");
  };

  const updateWeight = (key: "gross_weight_kg" | "tare_weight_kg", value: string) => {
    const next = { ...form, [key]: value };
    const gross = Number(next.gross_weight_kg);
    const tare = Number(next.tare_weight_kg);
    next.net_weight_kg = Number.isFinite(gross) && Number.isFinite(tare) ? Math.max(gross - tare, 0).toFixed(1) : "";
    setForm(next);
  };

  const handleSave = () => {
    if (!form.vehicle_id) {
      toast({ title: "Select truck number", description: "Search and select a truck before saving.", variant: "destructive" });
      return;
    }
    if (!form.dump_yard_id || !form.material_type) {
      toast({ title: "Missing dump details", description: "Select dump yard and material type.", variant: "destructive" });
      return;
    }
    const gross = Number(form.gross_weight_kg);
    const tare = Number(form.tare_weight_kg);
    const net = Number(form.net_weight_kg || netWeight);
    if (!Number.isFinite(gross) || !Number.isFinite(tare) || gross < 0 || tare < 0 || gross < tare) {
      toast({ title: "Invalid weights", description: "Gross and tare must be valid non-negative values, and gross must be greater than tare.", variant: "destructive" });
      return;
    }
    createMutation.mutate({
      vehicle_id: form.vehicle_id,
      gts_pickup_point_id: form.gts_pickup_point_id || null,
      dump_yard_id: form.dump_yard_id,
      material_type: form.material_type,
      service_date: form.service_date || today(),
      entry_time: form.entry_time ? new Date(form.entry_time).toISOString() : undefined,
      gross_weight_kg: gross,
      tare_weight_kg: tare,
      net_weight_kg: Number.isFinite(net) ? net : undefined,
      slip_number: form.slip_number || null,
      operator_name: form.operator_name || null,
      remarks: form.remarks || null,
    });
  };

  const handleExcelDownload = async () => {
    const rows = history as any[];
    if (!rows.length) {
      toast({
        title: "No weighment records",
        description: "There are no last-seven-days weighment records to export.",
        variant: "destructive",
      });
      return;
    }
    const periodFrom = sevenDaysAgo();
    const periodTo = today();
    try {
      const blob = await apiService.downloadDumpYardWeighmentExcel({
        date_from: periodFrom,
        date_to: periodTo,
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `dump_yard_weighment_last_7_days_${format(new Date(), "yyyyMMdd_HHmmss")}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast({
        title: "Excel report generated",
        description: "Professional backend-generated workbook downloaded.",
      });
    } catch (error) {
      toast({
        title: "Excel export failed",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    }
  };

  const detail = selectedVehicleDetails || selectedVehicle || {};
  const recentRows = (history as any[]).slice(0, 10);

  return (
    <div className="space-y-6">
      <PageHeader
        category="Master Entries"
        title="Dump Yard Weighment Entry"
        description="Fast truck lookup and direct dump yard weight capture without secondary assignment dependency"
        icon={Scale}
        badge={{ label: "Operator workflow", variant: "secondary" }}
        actions={
          <>
            <Button variant="outline" onClick={() => refetchHistory()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh History
            </Button>
            <Button onClick={handleExcelDownload} className="bg-emerald-700 hover:bg-emerald-800">
              <FileSpreadsheet className="mr-2 h-4 w-4" />
              Excel Report
            </Button>
          </>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Card className="overflow-hidden border-emerald-200/70 bg-gradient-to-br from-white via-emerald-50/35 to-amber-50/40 shadow-sm">
          <CardHeader className="border-b bg-white/70">
            <CardTitle className="flex items-center gap-2">
              <Truck className="h-5 w-5 text-emerald-700" />
              Truck Search & Weighment
            </CardTitle>
            <CardDescription>Type truck number, registration number, route, ward, or zone. Select once, then enter weights.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 p-5">
            <div className="relative">
              <Label className="text-sm font-semibold">Truck Number</Label>
              <div className="mt-2 flex items-center gap-3 rounded-2xl border border-emerald-200 bg-white px-4 py-3 shadow-sm focus-within:ring-2 focus-within:ring-emerald-500/25">
                <Search className="h-5 w-5 text-emerald-700" />
                <Input
                  value={truckQuery}
                  onChange={(event) => setTruckQuery(event.target.value)}
                  placeholder="Search MH12, 101, TRK..."
                  className="h-11 border-0 bg-transparent text-lg shadow-none focus-visible:ring-0"
                />
                {searchingTrucks && <Badge variant="outline">Searching</Badge>}
              </div>
              {debouncedTruckQuery && truckMatches.length > 0 && (
                <div className="absolute z-30 mt-2 max-h-72 w-full overflow-auto rounded-xl border bg-white p-2 shadow-xl">
                  {truckMatches.map((vehicle: any) => (
                    <button
                      key={vehicle.id}
                      type="button"
                      className="flex w-full items-center justify-between rounded-lg px-3 py-3 text-left hover:bg-emerald-50"
                      onClick={() => selectVehicle(vehicle)}
                    >
                      <span>
                        <span className="block font-semibold">{vehicle.vehicle_number}</span>
                        <span className="text-xs text-muted-foreground">
                          {vehicle.registration_number} | {fieldValue(vehicle.route_name)} | {fieldValue(vehicle.ward_name)}
                        </span>
                      </span>
                      <Badge className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100">
                        {fieldValue(vehicle.vehicle_category, "vehicle")}
                      </Badge>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {[
                ["Vehicle Number", detail.vehicle_number, Truck],
                ["Route", detail.route_name || detail.last_known_route, Route],
                ["Ward", detail.ward_name, MapPin],
                ["Zone", detail.zone_name, Building2],
                ["Driver", detail.driver_name, CheckCircle2],
                ["Vehicle Type", detail.vehicle_type || detail.truck_type, Truck],
                ["Material Mapping", detail.material_label || detail.material_type, PackageCheck],
                ["GTS / Dump Yard", `${fieldValue(detail.gts?.name)} -> ${fieldValue(detail.dump_yard?.name)}`, MapPin],
              ].map(([label, value, Icon]: any) => (
                <div key={label} className="rounded-xl border bg-white/80 p-3 shadow-sm">
                  <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    <Icon className="h-3.5 w-3.5 text-emerald-700" />
                    {label}
                  </div>
                  <div className="mt-1 min-h-6 font-semibold text-slate-900">{loadingVehicleDetails ? "Loading..." : fieldValue(value)}</div>
                </div>
              ))}
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <Label>Dump Yard</Label>
                <Select value={form.dump_yard_id} onValueChange={(value) => setForm({ ...form, dump_yard_id: value })}>
                  <SelectTrigger className="mt-2"><SelectValue placeholder="Select dump yard" /></SelectTrigger>
                  <SelectContent>
                    {(dumpYards as any[]).map((yard) => (
                      <SelectItem key={yard.id} value={String(yard.id)}>
                        {yard.dump_yard_name || yard.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Material Type</Label>
                <Select value={form.material_type} onValueChange={(value) => setForm({ ...form, material_type: value })}>
                  <SelectTrigger className="mt-2"><SelectValue placeholder="Select material" /></SelectTrigger>
                  <SelectContent>
                    {(materialTypes as any[]).map((item) => (
                      <SelectItem key={item.value} value={String(item.value)}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Entry Time</Label>
                <Input className="mt-2" type="datetime-local" value={form.entry_time} onChange={(event) => setForm({ ...form, entry_time: event.target.value })} />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-4">
              <div>
                <Label>Gross Weight KG</Label>
                <Input className="mt-2 text-lg font-semibold" type="number" min="0" value={form.gross_weight_kg} onChange={(event) => updateWeight("gross_weight_kg", event.target.value)} />
              </div>
              <div>
                <Label>Tare Weight KG</Label>
                <Input className="mt-2 text-lg font-semibold" type="number" min="0" value={form.tare_weight_kg} onChange={(event) => updateWeight("tare_weight_kg", event.target.value)} />
              </div>
              <div>
                <Label>Net Weight KG</Label>
                <Input className="mt-2 text-lg font-semibold text-emerald-700" type="number" min="0" value={form.net_weight_kg || netWeight} onChange={(event) => setForm({ ...form, net_weight_kg: event.target.value })} />
              </div>
              <div>
                <Label>Service Date</Label>
                <Input className="mt-2" type="date" value={form.service_date} onChange={(event) => setForm({ ...form, service_date: event.target.value })} />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <Label>Slip Number</Label>
                <Input className="mt-2" value={form.slip_number} onChange={(event) => setForm({ ...form, slip_number: event.target.value })} placeholder="Optional" />
              </div>
              <div>
                <Label>Operator Name</Label>
                <Input className="mt-2" value={form.operator_name} onChange={(event) => setForm({ ...form, operator_name: event.target.value })} placeholder="Optional" />
              </div>
              <div>
                <Label>Remarks</Label>
                <Input className="mt-2" value={form.remarks} onChange={(event) => setForm({ ...form, remarks: event.target.value })} placeholder="Optional note" />
              </div>
            </div>

            <div className="flex flex-col gap-3 rounded-2xl border border-emerald-200 bg-white/80 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="text-sm font-semibold">Ready to save direct vehicle weighment</div>
                <div className="text-xs text-muted-foreground">Duplicate submissions for the same truck/material/dump yard within 2 minutes are blocked by the API.</div>
              </div>
              <Button size="lg" disabled={createMutation.isPending} onClick={handleSave} className="bg-emerald-700 hover:bg-emerald-800">
                <Scale className="mr-2 h-4 w-4" />
                {createMutation.isPending ? "Saving..." : "Save Weighment"}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-amber-600" />
              Recent Entries
            </CardTitle>
            <CardDescription>Latest 10 weighments from the last 7 days.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-xl border">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead>Time</TableHead>
                    <TableHead>Truck</TableHead>
                    <TableHead>Material</TableHead>
                    <TableHead className="text-right">Net KG</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentRows.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">
                        No recent weighment records.
                      </TableCell>
                    </TableRow>
                  ) : (
                    recentRows.map((row: any) => (
                      <TableRow key={row.id}>
                        <TableCell className="whitespace-nowrap text-xs">{row.entry_time ? format(new Date(row.entry_time), "dd MMM, HH:mm") : fieldValue(row.service_date)}</TableCell>
                        <TableCell>
                          <div className="font-medium">{fieldValue(row.vehicle_number)}</div>
                          <div className="text-xs text-muted-foreground">{fieldValue(row.route_name)}</div>
                        </TableCell>
                        <TableCell><Badge variant="secondary">{fieldValue(row.material_label || row.material_type)}</Badge></TableCell>
                        <TableCell className="text-right font-semibold">{Number(row.net_weight_kg || 0).toFixed(1)}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
