import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Edit, MapPin, Plus, Search, Trash2, Warehouse } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { useWards } from "@/hooks/useDataQueries";
import { apiService } from "@/services/api";

const PAGE_SIZE = 8;

const emptyGts = {
  name: "",
  latitude: "",
  longitude: "",
  address: "",
  ward_id: "",
  zone_id: "",
  is_active: true,
};

const emptyDumpYard = {
  name: "",
  latitude: "",
  longitude: "",
  address: "",
  capacity: "",
  is_active: true,
};

export default function MasterGtsDumpYards() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: wards = [] } = useWards();
  const [tab, setTab] = useState("gts");
  const [gtsSearch, setGtsSearch] = useState("");
  const [dumpSearch, setDumpSearch] = useState("");
  const [gtsPage, setGtsPage] = useState(1);
  const [dumpPage, setDumpPage] = useState(1);
  const [gtsDialogOpen, setGtsDialogOpen] = useState(false);
  const [dumpDialogOpen, setDumpDialogOpen] = useState(false);
  const [editingGts, setEditingGts] = useState<any | null>(null);
  const [editingDump, setEditingDump] = useState<any | null>(null);
  const [gtsForm, setGtsForm] = useState<any>(emptyGts);
  const [dumpForm, setDumpForm] = useState<any>(emptyDumpYard);

  const wardById = useMemo(() => new Map((wards as any[]).map((ward) => [String(ward.id), ward.name || ward.ward_name])), [wards]);

  const { data: gtsPayload = { items: [], total: 0 }, isLoading: gtsLoading } = useQuery({
    queryKey: ["gts", gtsSearch, gtsPage],
    queryFn: () => apiService.getGts({ q: gtsSearch, page: String(gtsPage), page_size: String(PAGE_SIZE) }),
  });

  const { data: dumpYards = [], isLoading: dumpLoading } = useQuery({
    queryKey: ["dump-yards-master"],
    queryFn: () => apiService.getDumpYards(),
  });

  const filteredDumpYards = useMemo(() => {
    const q = dumpSearch.trim().toLowerCase();
    if (!q) return dumpYards as any[];
    return (dumpYards as any[]).filter((row) => String(row.name || row.dump_yard_name || "").toLowerCase().includes(q));
  }, [dumpYards, dumpSearch]);

  const pagedDumpYards = filteredDumpYards.slice((dumpPage - 1) * PAGE_SIZE, dumpPage * PAGE_SIZE);
  const dumpTotalPages = Math.max(1, Math.ceil(filteredDumpYards.length / PAGE_SIZE));
  const gtsTotalPages = Math.max(1, Math.ceil(Number(gtsPayload.total || 0) / PAGE_SIZE));

  const resetGts = () => {
    setEditingGts(null);
    setGtsForm(emptyGts);
    setGtsDialogOpen(false);
  };

  const resetDump = () => {
    setEditingDump(null);
    setDumpForm(emptyDumpYard);
    setDumpDialogOpen(false);
  };

  const openEditGts = (row: any) => {
    setEditingGts(row);
    setGtsForm({
      name: row.name || "",
      latitude: row.latitude ?? "",
      longitude: row.longitude ?? "",
      address: row.address || "",
      ward_id: row.ward_id || "",
      zone_id: row.zone_id || "",
      is_active: row.is_active !== false,
    });
    setGtsDialogOpen(true);
  };

  const openEditDump = (row: any) => {
    setEditingDump(row);
    setDumpForm({
      name: row.name || row.dump_yard_name || "",
      latitude: row.latitude ?? row.lat ?? "",
      longitude: row.longitude ?? row.lng ?? "",
      address: row.address || "",
      capacity: row.capacity ?? "",
      is_active: row.is_active !== false,
    });
    setDumpDialogOpen(true);
  };

  const saveGts = async () => {
    if (!gtsForm.name.trim()) {
      toast({ title: "GTS name required", variant: "destructive" });
      return;
    }
    const selectedWard = (wards as any[]).find((ward) => String(ward.id) === String(gtsForm.ward_id));
    const payload = {
      name: gtsForm.name.trim(),
      latitude: gtsForm.latitude === "" ? null : Number(gtsForm.latitude),
      longitude: gtsForm.longitude === "" ? null : Number(gtsForm.longitude),
      address: gtsForm.address || null,
      ward_id: gtsForm.ward_id || null,
      zone_id: selectedWard?.zoneId || selectedWard?.zone_id || gtsForm.zone_id || null,
      is_active: Boolean(gtsForm.is_active),
    };
    try {
      if (editingGts) await apiService.updateGts(String(editingGts.id), payload);
      else await apiService.createGts(payload);
      toast({ title: editingGts ? "GTS updated" : "GTS created" });
      await queryClient.invalidateQueries({ queryKey: ["gts"] });
      resetGts();
    } catch (error) {
      toast({ title: "Unable to save GTS", description: error instanceof Error ? error.message : "Please try again", variant: "destructive" });
    }
  };

  const saveDump = async () => {
    if (!dumpForm.name.trim()) {
      toast({ title: "Dump Yard name required", variant: "destructive" });
      return;
    }
    const payload = {
      name: dumpForm.name.trim(),
      latitude: dumpForm.latitude === "" ? null : Number(dumpForm.latitude),
      longitude: dumpForm.longitude === "" ? null : Number(dumpForm.longitude),
      address: dumpForm.address || null,
      capacity: dumpForm.capacity === "" ? null : Number(dumpForm.capacity),
      is_active: Boolean(dumpForm.is_active),
    };
    try {
      if (editingDump) await apiService.updateDumpYard(String(editingDump.id), payload);
      else await apiService.createDumpYard(payload);
      toast({ title: editingDump ? "Dump Yard updated" : "Dump Yard created" });
      await queryClient.invalidateQueries({ queryKey: ["dump-yards-master"] });
      resetDump();
    } catch (error) {
      toast({ title: "Unable to save Dump Yard", description: error instanceof Error ? error.message : "Please try again", variant: "destructive" });
    }
  };

  const deleteGts = async (id: string) => {
    if (!window.confirm("Delete this GTS point?")) return;
    await apiService.deleteGts(id);
    await queryClient.invalidateQueries({ queryKey: ["gts"] });
    toast({ title: "GTS deleted" });
  };

  const deleteDump = async (id: string) => {
    if (!window.confirm("Delete this Dump Yard?")) return;
    await apiService.deleteDumpYard(id);
    await queryClient.invalidateQueries({ queryKey: ["dump-yards-master"] });
    toast({ title: "Dump Yard deleted" });
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Master Data"
        title="GTS & Dump Yard Master"
        description="Garbage Transport Station and Dump Yard point management"
        icon={Warehouse}
      />

      <Tabs value={tab} onValueChange={setTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="gts">GTS Master</TabsTrigger>
          <TabsTrigger value="dump-yard">Dump Yard Master</TabsTrigger>
        </TabsList>

        <TabsContent value="gts">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2"><MapPin className="h-5 w-5 text-primary" /> GTS Master</CardTitle>
              <Dialog open={gtsDialogOpen} onOpenChange={(open) => { if (!open) resetGts(); setGtsDialogOpen(open); }}>
                <DialogTrigger asChild><Button><Plus className="h-4 w-4 mr-2" /> Add GTS</Button></DialogTrigger>
                <DialogContent>
                  <DialogHeader><DialogTitle>{editingGts ? "Edit GTS" : "Add GTS"}</DialogTitle><DialogDescription>GTS = Garbage Transport Station.</DialogDescription></DialogHeader>
                  <div className="grid gap-4">
                    <div><Label>Name</Label><Input value={gtsForm.name} onChange={(e) => setGtsForm({ ...gtsForm, name: e.target.value })} /></div>
                    <div><Label>Ward</Label><Select value={gtsForm.ward_id || "none"} onValueChange={(v) => setGtsForm({ ...gtsForm, ward_id: v === "none" ? "" : v })}><SelectTrigger><SelectValue placeholder="Select ward" /></SelectTrigger><SelectContent><SelectItem value="none">No Ward</SelectItem>{(wards as any[]).map((ward) => <SelectItem key={ward.id} value={String(ward.id)}>{ward.name || ward.ward_name}</SelectItem>)}</SelectContent></Select></div>
                    <div className="grid grid-cols-2 gap-3">
                      <div><Label>Latitude</Label><Input type="number" value={gtsForm.latitude} onChange={(e) => setGtsForm({ ...gtsForm, latitude: e.target.value })} /></div>
                      <div><Label>Longitude</Label><Input type="number" value={gtsForm.longitude} onChange={(e) => setGtsForm({ ...gtsForm, longitude: e.target.value })} /></div>
                    </div>
                    <div><Label>Address</Label><Input value={gtsForm.address} onChange={(e) => setGtsForm({ ...gtsForm, address: e.target.value })} /></div>
                    <div><Label>Status</Label><Select value={gtsForm.is_active ? "active" : "inactive"} onValueChange={(v) => setGtsForm({ ...gtsForm, is_active: v === "active" })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="active">Active</SelectItem><SelectItem value="inactive">Inactive</SelectItem></SelectContent></Select></div>
                  </div>
                  <DialogFooter><Button variant="outline" onClick={resetGts}>Cancel</Button><Button onClick={saveGts}>Save</Button></DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="relative max-w-md"><Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" /><Input className="pl-10" placeholder="Search GTS..." value={gtsSearch} onChange={(e) => { setGtsSearch(e.target.value); setGtsPage(1); }} /></div>
              <Table>
                <TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Ward</TableHead><TableHead>Location</TableHead><TableHead>Address</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
                <TableBody>
                  {gtsLoading ? <TableRow><TableCell colSpan={6}>Loading...</TableCell></TableRow> : (gtsPayload.items || []).map((row: any) => (
                    <TableRow key={row.id}>
                      <TableCell className="font-medium">{row.name}</TableCell>
                      <TableCell>{wardById.get(String(row.ward_id || "")) || "-"}</TableCell>
                      <TableCell>{row.latitude ?? "-"}, {row.longitude ?? "-"}</TableCell>
                      <TableCell>{row.address || "-"}</TableCell>
                      <TableCell><Badge variant={row.is_active ? "default" : "secondary"}>{row.is_active ? "Active" : "Inactive"}</Badge></TableCell>
                      <TableCell className="text-right"><Button size="icon" variant="ghost" onClick={() => openEditGts(row)}><Edit className="h-4 w-4" /></Button><Button size="icon" variant="ghost" className="text-destructive" onClick={() => deleteGts(String(row.id))}><Trash2 className="h-4 w-4" /></Button></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="flex justify-end gap-2"><Button variant="outline" size="sm" disabled={gtsPage <= 1} onClick={() => setGtsPage(gtsPage - 1)}>Prev</Button><Button variant="outline" size="sm" disabled={gtsPage >= gtsTotalPages} onClick={() => setGtsPage(gtsPage + 1)}>Next</Button></div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="dump-yard">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2"><Building2 className="h-5 w-5 text-primary" /> Dump Yard Master</CardTitle>
              <Dialog open={dumpDialogOpen} onOpenChange={(open) => { if (!open) resetDump(); setDumpDialogOpen(open); }}>
                <DialogTrigger asChild><Button><Plus className="h-4 w-4 mr-2" /> Add Dump Yard</Button></DialogTrigger>
                <DialogContent>
                  <DialogHeader><DialogTitle>{editingDump ? "Edit Dump Yard" : "Add Dump Yard"}</DialogTitle><DialogDescription>Dump yard location and capacity master.</DialogDescription></DialogHeader>
                  <div className="grid gap-4">
                    <div><Label>Name</Label><Input value={dumpForm.name} onChange={(e) => setDumpForm({ ...dumpForm, name: e.target.value })} /></div>
                    <div className="grid grid-cols-2 gap-3"><div><Label>Latitude</Label><Input type="number" value={dumpForm.latitude} onChange={(e) => setDumpForm({ ...dumpForm, latitude: e.target.value })} /></div><div><Label>Longitude</Label><Input type="number" value={dumpForm.longitude} onChange={(e) => setDumpForm({ ...dumpForm, longitude: e.target.value })} /></div></div>
                    <div><Label>Address</Label><Input value={dumpForm.address} onChange={(e) => setDumpForm({ ...dumpForm, address: e.target.value })} /></div>
                    <div><Label>Capacity</Label><Input type="number" value={dumpForm.capacity} onChange={(e) => setDumpForm({ ...dumpForm, capacity: e.target.value })} /></div>
                    <div><Label>Status</Label><Select value={dumpForm.is_active ? "active" : "inactive"} onValueChange={(v) => setDumpForm({ ...dumpForm, is_active: v === "active" })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="active">Active</SelectItem><SelectItem value="inactive">Inactive</SelectItem></SelectContent></Select></div>
                  </div>
                  <DialogFooter><Button variant="outline" onClick={resetDump}>Cancel</Button><Button onClick={saveDump}>Save</Button></DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="relative max-w-md"><Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" /><Input className="pl-10" placeholder="Search dump yard..." value={dumpSearch} onChange={(e) => { setDumpSearch(e.target.value); setDumpPage(1); }} /></div>
              <Table>
                <TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Location</TableHead><TableHead>Address</TableHead><TableHead>Capacity</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
                <TableBody>
                  {dumpLoading ? <TableRow><TableCell colSpan={6}>Loading...</TableCell></TableRow> : pagedDumpYards.map((row: any) => (
                    <TableRow key={row.id}>
                      <TableCell className="font-medium">{row.name || row.dump_yard_name}</TableCell>
                      <TableCell>{row.latitude ?? row.lat ?? "-"}, {row.longitude ?? row.lng ?? "-"}</TableCell>
                      <TableCell>{row.address || "-"}</TableCell>
                      <TableCell>{row.capacity ?? "-"}</TableCell>
                      <TableCell><Badge variant={row.is_active ? "default" : "secondary"}>{row.is_active ? "Active" : "Inactive"}</Badge></TableCell>
                      <TableCell className="text-right"><Button size="icon" variant="ghost" onClick={() => openEditDump(row)}><Edit className="h-4 w-4" /></Button><Button size="icon" variant="ghost" className="text-destructive" onClick={() => deleteDump(String(row.id))}><Trash2 className="h-4 w-4" /></Button></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="flex justify-end gap-2"><Button variant="outline" size="sm" disabled={dumpPage <= 1} onClick={() => setDumpPage(dumpPage - 1)}>Prev</Button><Button variant="outline" size="sm" disabled={dumpPage >= dumpTotalPages} onClick={() => setDumpPage(dumpPage + 1)}>Next</Button></div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
