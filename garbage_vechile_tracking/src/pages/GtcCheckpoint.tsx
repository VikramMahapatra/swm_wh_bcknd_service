import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { format, subDays } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { useToast } from "@/hooks/use-toast";
import { useGtcCheckpoints, useTrucks } from "@/hooks/useDataQueries";
import { apiService } from "@/services/api";
import { CalendarClock, ClipboardCheck, Gauge, Search, ShieldCheck, Truck } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";

const SCORE_MIN = 0;
const SCORE_MAX = 10;

const wasteOptions = [
  { key: "dry", label: "Dry" },
  { key: "wet", label: "Wet" },
  { key: "metal", label: "Metal" },
  { key: "plastic", label: "Plastic" },
  { key: "sanitary", label: "Sanitary" },
] as const;

const getLocalDateTimeValue = () => {
  const now = new Date();
  const offsetMs = now.getTimezoneOffset() * 60 * 1000;
  return new Date(now.getTime() - offsetMs).toISOString().slice(0, 16);
};

const formatDateTime = (value?: string) => {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "-";
  return format(parsed, "yyyy-MM-dd HH:mm");
};

export default function GtcCheckpoint() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: trucksData = [] } = useTrucks();

  const [filterTruckId, setFilterTruckId] = useState<string>("all");
  const [filterDateFrom, setFilterDateFrom] = useState<string>(
    format(subDays(new Date(), 10), "yyyy-MM-dd")
  );
  const [filterDateTo, setFilterDateTo] = useState<string>(format(new Date(), "yyyy-MM-dd"));

  const { data: checkpoints = [], isLoading: isLoadingCheckpoints } = useGtcCheckpoints({
    truck_id: filterTruckId === "all" ? undefined : filterTruckId,
    date_from: filterDateFrom || undefined,
    date_to: filterDateTo || undefined,
  });

  const trucks = useMemo(() => {
    return (trucksData as any[]).map((truck) => ({
      id: truck.id,
      registrationNumber: truck.registrationNumber || truck.registration_number || truck.id,
    }));
  }, [trucksData]);

  const [formTruckId, setFormTruckId] = useState<string>("");
  const [formArrivedAt, setFormArrivedAt] = useState<string>(getLocalDateTimeValue());
  const [formWaste, setFormWaste] = useState({
    dry: false,
    wet: false,
    metal: false,
    plastic: false,
    sanitary: false,
  });
  const [truckScore, setTruckScore] = useState<string>("");
  const [gtcScore, setGtcScore] = useState<string>("");
  const [remarks, setRemarks] = useState<string>("");
  const [isSaving, setIsSaving] = useState(false);

  const summary = useMemo(() => {
    const entries = checkpoints as any[];
    const truckSet = new Set(entries.map((entry) => entry.truck_id));
    const truckScores = entries
      .map((entry) => entry.truck_cleanliness_score)
      .filter((value) => typeof value === "number") as number[];
    const gtcScores = entries
      .map((entry) => entry.gtc_cleanliness_score)
      .filter((value) => typeof value === "number") as number[];

    const avgTruckScore = truckScores.length
      ? truckScores.reduce((sum, value) => sum + value, 0) / truckScores.length
      : null;
    const avgGtcScore = gtcScores.length
      ? gtcScores.reduce((sum, value) => sum + value, 0) / gtcScores.length
      : null;

    return {
      totalEntries: entries.length,
      uniqueTrucks: truckSet.size,
      avgTruckScore,
      avgGtcScore,
    };
  }, [checkpoints]);

  const handleWasteToggle = (key: keyof typeof formWaste) => {
    setFormWaste((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const hasSelectedWaste = Object.values(formWaste).some(Boolean);

  const parseScore = (value: string) => {
    if (!value.trim()) return null;
    const parsed = Number(value);
    if (Number.isNaN(parsed)) return null;
    return parsed;
  };

  const validateScore = (value: number | null) => {
    if (value === null) return true;
    return value >= SCORE_MIN && value <= SCORE_MAX;
  };

  const handleSliderChange = (value: number[], target: "truck" | "gtc") => {
    const nextValue = value[0]?.toString() ?? "";
    if (target === "truck") {
      setTruckScore(nextValue);
    } else {
      setGtcScore(nextValue);
    }
  };

  const resetForm = () => {
    setFormTruckId("");
    setFormArrivedAt(getLocalDateTimeValue());
    setFormWaste({ dry: false, wet: false, metal: false, plastic: false, sanitary: false });
    setTruckScore("");
    setGtcScore("");
    setRemarks("");
  };

  const handleSubmit = async () => {
    if (!formTruckId) {
      toast({ title: "Select a truck", description: "Please choose a truck before saving.", variant: "destructive" });
      return;
    }

    if (!hasSelectedWaste) {
      toast({ title: "Select garbage type", description: "Pick at least one garbage type.", variant: "destructive" });
      return;
    }

    const parsedTruckScore = parseScore(truckScore);
    const parsedGtcScore = parseScore(gtcScore);

    if (!validateScore(parsedTruckScore) || !validateScore(parsedGtcScore)) {
      toast({
        title: "Invalid score",
        description: `Scores must be between ${SCORE_MIN} and ${SCORE_MAX}.`,
        variant: "destructive",
      });
      return;
    }

    const payload = {
      truck_id: formTruckId,
      arrived_at: formArrivedAt ? new Date(formArrivedAt).toISOString() : undefined,
      is_dry: formWaste.dry,
      is_wet: formWaste.wet,
      is_metal: formWaste.metal,
      is_plastic: formWaste.plastic,
      is_sanitary: formWaste.sanitary,
      truck_cleanliness_score: parsedTruckScore,
      gtc_cleanliness_score: parsedGtcScore,
      remarks: remarks.trim() ? remarks.trim() : null,
    };

    try {
      setIsSaving(true);
      await apiService.createGtcCheckpoint(payload);
      toast({ title: "Checkpoint saved", description: "GTC entry has been recorded." });
      resetForm();
      queryClient.invalidateQueries({ queryKey: ["gtc-checkpoints"] });
    } catch (error) {
      toast({ title: "Save failed", description: "Could not save the checkpoint entry.", variant: "destructive" });
    } finally {
      setIsSaving(false);
    }
  };

  const wasteBadges = (entry: any) => {
    const badges = [];
    if (entry.is_dry) badges.push("Dry");
    if (entry.is_wet) badges.push("Wet");
    if (entry.is_metal) badges.push("Metal");
    if (entry.is_plastic) badges.push("Plastic");
    if (entry.is_sanitary) badges.push("Sanitary");
    if (badges.length === 0) return <Badge variant="secondary">None</Badge>;
    return badges.map((label) => (
      <Badge key={label} variant="outline" className="mr-1">
        {label}
      </Badge>
    ));
  };

  const renderScoreBadge = (score: number | null | undefined, label: "truck" | "gtc") => {
    if (score === null || score === undefined) {
      return <Badge variant="outline">-</Badge>;
    }
    
    const isHighScore = score > 7;
    
    if (isHighScore) {
      return (
        <div className="flex flex-col gap-1">
          <Badge className="bg-gradient-to-r from-emerald-500 to-green-600 text-white border-0 font-semibold shadow-sm">
            {score}
          </Badge>
          <Badge variant="outline" className="text-[10px] border-emerald-300 text-emerald-700 bg-emerald-50">
            High
          </Badge>
        </div>
      );
    }
    
    return (
      <Badge variant="outline" className="border-emerald-200 text-emerald-700">
        {score}
      </Badge>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/30">
      <div className="container mx-auto px-4 py-6 space-y-6">
        <PageHeader
          category="Verification"
          title="GTC Checkpoint"
          description="Log truck arrivals, garbage types, and cleanliness scores in real time"
          icon={ClipboardCheck}
          actions={
            <div className="flex gap-3">
              <div className="rounded-lg border border-emerald-200/70 bg-white/80 px-4 py-2 shadow-sm">
                <div className="text-xs text-muted-foreground">Total Entries</div>
                <div className="text-lg font-semibold text-emerald-800">{summary.totalEntries}</div>
              </div>
              <div className="rounded-lg border border-emerald-100/70 bg-white/80 px-4 py-2 shadow-sm">
                <div className="text-xs text-muted-foreground">Unique Trucks</div>
                <div className="text-lg font-semibold text-emerald-700">{summary.uniqueTrucks}</div>
              </div>
            </div>
          }
        />

        <div className="grid gap-4 md:grid-cols-4">
          <Card className="p-4 border-l-4 border-l-emerald-500">
            <CardContent className="p-0">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-muted-foreground">Avg Truck Score</div>
                  <div className="text-2xl font-bold text-emerald-700">
                    {summary.avgTruckScore === null ? "-" : summary.avgTruckScore.toFixed(1)}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">Across all recorded entries</div>
                </div>
                <div className="h-12 w-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                  <Truck className="h-6 w-6 text-emerald-700" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="p-4 border-l-4 border-l-emerald-400">
            <CardContent className="p-0">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-muted-foreground">Avg GTC Score</div>
                  <div className="text-2xl font-bold text-emerald-700">
                    {summary.avgGtcScore === null ? "-" : summary.avgGtcScore.toFixed(1)}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">Cleanliness rating at GTC</div>
                </div>
                <div className="h-12 w-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                  <ShieldCheck className="h-6 w-6 text-emerald-700" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="p-4 border-l-4 border-l-emerald-300">
            <CardContent className="p-0">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-muted-foreground">Filter Start</div>
                  <div className="text-2xl font-bold text-emerald-700">{filterDateFrom || "-"}</div>
                  <div className="mt-1 text-xs text-muted-foreground">Start of selected range</div>
                </div>
                <div className="h-12 w-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                  <CalendarClock className="h-6 w-6 text-emerald-700" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="p-4 border-l-4 border-l-lime-400">
            <CardContent className="p-0">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-muted-foreground">Filter End</div>
                  <div className="text-2xl font-bold text-lime-700">{filterDateTo || "-"}</div>
                  <div className="mt-1 text-xs text-muted-foreground">End of selected range</div>
                </div>
                <div className="h-12 w-12 rounded-xl bg-lime-500/10 flex items-center justify-center">
                  <Gauge className="h-6 w-6 text-lime-700" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="p-4 border-l-4 border-l-emerald-500 bg-gradient-to-br from-emerald-50/60 via-background to-lime-50/50">
          <CardHeader className="p-0 pb-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <CardTitle className="text-lg">New Checkpoint Entry</CardTitle>
                <p className="text-sm text-muted-foreground">Record each truck arrival, waste type, and hygiene score.</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="border-emerald-200 text-emerald-700">Scores scale: 0 to 10</Badge>
                <Badge className="bg-emerald-100 text-emerald-700">Live entry</Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="space-y-4">
              <div className="rounded-xl border border-emerald-100/70 bg-white/70 p-4 shadow-sm">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Truck</Label>
                    <Select value={formTruckId} onValueChange={setFormTruckId}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select truck" />
                      </SelectTrigger>
                      <SelectContent>
                        {trucks.map((truck) => (
                          <SelectItem key={truck.id} value={truck.id}>
                            {truck.registrationNumber}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Arrival Time</Label>
                    <Input
                      type="datetime-local"
                      value={formArrivedAt}
                      onChange={(event) => setFormArrivedAt(event.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-emerald-100/70 bg-white/70 p-4 shadow-sm">
                <div className="space-y-3">
                  <Label>Garbage Types</Label>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                    {wasteOptions.map((option) => (
                      <label
                        key={option.key}
                        className="flex items-center gap-2 rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-sm"
                      >
                        <Checkbox
                          checked={formWaste[option.key]}
                          onCheckedChange={() => handleWasteToggle(option.key)}
                        />
                        {option.label}
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-3">
                <div className="space-y-3 rounded-xl border border-emerald-100/70 bg-white/70 p-4 shadow-sm">
                  <div className="flex items-center justify-between">
                    <Label>Truck Cleanliness Score</Label>
                    <Badge className="bg-emerald-100 text-emerald-700">{truckScore || "-"}</Badge>
                  </div>
                  <Slider
                    min={SCORE_MIN}
                    max={SCORE_MAX}
                    step={1}
                    value={[parseScore(truckScore) ?? SCORE_MIN]}
                    onValueChange={(value) => handleSliderChange(value, "truck")}
                  />
                  <Input
                    type="number"
                    min={SCORE_MIN}
                    max={SCORE_MAX}
                    value={truckScore}
                    onChange={(event) => setTruckScore(event.target.value)}
                    placeholder="Optional"
                  />
                </div>
                <div className="space-y-3 rounded-xl border border-emerald-100/70 bg-white/70 p-4 shadow-sm">
                  <div className="flex items-center justify-between">
                    <Label>GTC Cleanliness Score</Label>
                    <Badge className="bg-emerald-100 text-emerald-700">{gtcScore || "-"}</Badge>
                  </div>
                  <Slider
                    min={SCORE_MIN}
                    max={SCORE_MAX}
                    step={1}
                    value={[parseScore(gtcScore) ?? SCORE_MIN]}
                    onValueChange={(value) => handleSliderChange(value, "gtc")}
                  />
                  <Input
                    type="number"
                    min={SCORE_MIN}
                    max={SCORE_MAX}
                    value={gtcScore}
                    onChange={(event) => setGtcScore(event.target.value)}
                    placeholder="Optional"
                  />
                </div>
                <div className="space-y-2 rounded-xl border border-emerald-100/70 bg-white/70 p-4 shadow-sm">
                  <Label>Remarks</Label>
                  <Textarea
                    value={remarks}
                    onChange={(event) => setRemarks(event.target.value)}
                    placeholder="Optional notes"
                    rows={5}
                  />
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-muted-foreground">Tip: include both scores for a complete audit.</p>
                <div className="flex flex-wrap justify-end gap-2">
                  <Button variant="outline" onClick={resetForm} disabled={isSaving}>
                    Clear
                  </Button>
                  <Button onClick={handleSubmit} disabled={isSaving}>
                    {isSaving ? "Saving..." : "Save Entry"}
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="p-4">
          <CardHeader className="p-0 pb-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="text-lg">Checkpoint Entries</CardTitle>
              <Badge className="bg-emerald-100 text-emerald-700">{summary.totalEntries} records</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="space-y-4">
              <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                <div className="flex items-center gap-2 text-sm font-medium text-emerald-700">
                  <Search className="h-4 w-4" />
                  Filter entries
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label>Truck</Label>
                    <Select value={filterTruckId} onValueChange={setFilterTruckId}>
                      <SelectTrigger>
                        <SelectValue placeholder="All trucks" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All trucks</SelectItem>
                        {trucks.map((truck) => (
                          <SelectItem key={truck.id} value={truck.id}>
                            {truck.registrationNumber}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Date From</Label>
                    <Input type="date" value={filterDateFrom} onChange={(event) => setFilterDateFrom(event.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label>Date To</Label>
                    <Input type="date" value={filterDateTo} onChange={(event) => setFilterDateTo(event.target.value)} />
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-xs border-emerald-200 text-emerald-700 bg-emerald-50/60 hover:bg-emerald-100"
                    onClick={() => {
                      setFilterDateFrom(format(subDays(new Date(), 10), "yyyy-MM-dd"));
                      setFilterDateTo(format(new Date(), "yyyy-MM-dd"));
                    }}
                  >
                    Last 10 days
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-xs border-lime-200 text-lime-700 bg-lime-50/70 hover:bg-lime-100"
                    onClick={() => {
                      const today = format(new Date(), "yyyy-MM-dd");
                      setFilterDateFrom(today);
                      setFilterDateTo(today);
                    }}
                  >
                    Today
                  </Button>
                </div>
              </div>

              <div className="overflow-hidden rounded-xl border border-border/60 bg-background shadow-sm">
              <Table>
                <TableHeader>
                  <TableRow className="bg-emerald-50/70">
                    <TableHead>Date & Time</TableHead>
                    <TableHead>Truck</TableHead>
                    <TableHead>Garbage Types</TableHead>
                    <TableHead>Truck Score</TableHead>
                    <TableHead>GTC Score</TableHead>
                    <TableHead>Remarks</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoadingCheckpoints ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground">
                        Loading entries...
                      </TableCell>
                    </TableRow>
                  ) : checkpoints.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground">
                        No entries found.
                      </TableCell>
                    </TableRow>
                  ) : (
                    (checkpoints as any[]).map((entry) => (
                      <TableRow 
                        key={entry.id} 
                        className={`hover:bg-muted/20 ${
                          (entry.truck_cleanliness_score > 7 || entry.gtc_cleanliness_score > 7)
                            ? 'bg-emerald-50/30 border-l-4 border-l-emerald-400'
                            : ''
                        }`}
                      >
                        <TableCell>{formatDateTime(entry.arrived_at)}</TableCell>
                        <TableCell className="font-medium">
                          {entry.truck_registration_number || entry.truck_id}
                        </TableCell>
                        <TableCell>{wasteBadges(entry)}</TableCell>
                        <TableCell>{renderScoreBadge(entry.truck_cleanliness_score, "truck")}</TableCell>
                        <TableCell>{renderScoreBadge(entry.gtc_cleanliness_score, "gtc")}</TableCell>
                        <TableCell className="max-w-[240px] truncate" title={entry.remarks || ""}>
                          {entry.remarks || "-"}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
