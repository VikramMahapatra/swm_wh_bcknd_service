import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import { useTickets } from '@/hooks/useDataQueries';
import type { Ticket, TicketStatus, TicketPriority, TicketCategory, TicketComment } from '@/data/tickets';
import { slaConfig } from '@/data/tickets';
import { PageHeader } from '@/components/PageHeader';
import { Loader2, AlertCircle } from 'lucide-react';
import { Plus, Search, Clock, AlertTriangle, CheckCircle, MessageSquare, ArrowUpRight, Filter, Download, User, Calendar, Tag, Ticket as TicketIcon } from 'lucide-react';
import { format, differenceInMinutes, parseISO } from 'date-fns';

const getDateValue = (value: unknown): string | undefined =>
  typeof value === 'string' && value.trim() ? value : undefined;

const safeParseISO = (value?: string) => (value ? parseISO(value) : null);

export default function Tickets() {
  const { toast } = useToast();
  const { data: ticketsData = [], isLoading: isLoadingTickets, error: ticketsError } = useTickets();
  
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [newComment, setNewComment] = useState('');

  useEffect(() => {
    const normalizedTickets = (ticketsData as any[]).map((ticket) => ({
      id: ticket.id || ticket.ticket_number || 'UNKNOWN',
      title: ticket.title || 'Untitled',
      description: ticket.description || '',
      category: ticket.category || 'complaint',
      priority: ticket.priority || 'medium',
      status: ticket.status || 'open',
      createdAt: ticket.createdAt || ticket.created_at || new Date().toISOString(),
      updatedAt: ticket.updatedAt || ticket.updated_at || new Date().toISOString(),
      dueDate: ticket.dueDate || ticket.due_date || new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      assignedTo: ticket.assignedTo || ticket.assigned_to || '',
      createdBy: ticket.createdBy || ticket.reporter_name || 'System',
      escalationLevel: ticket.escalationLevel ?? 0,
      slaBreached: ticket.slaBreached ?? ticket.sla_breached ?? false,
      comments: ticket.comments || [],
    })) as Ticket[];

    setTickets(normalizedTickets);
    if (ticketsError) {
      toast({ title: "Error", description: "Failed to load tickets", variant: "destructive" });
    }
  }, [ticketsData, ticketsError, toast]);
  
  const [formData, setFormData] = useState<Partial<Ticket>>({
    title: '',
    description: '',
    category: 'complaint',
    priority: 'medium',
    dueDate: '',
    assignedTo: ''
  });

  const getStatusBadge = (status: TicketStatus) => {
    const styles: Record<TicketStatus, string> = {
      open: 'bg-blue-500/20 text-blue-600 border-blue-500/30',
      in_progress: 'bg-primary/20 text-primary border-primary/30',
      pending: 'bg-warning/20 text-warning border-warning/30',
      resolved: 'bg-success/20 text-success border-success/30',
      closed: 'bg-muted text-muted-foreground border-border'
    };
    return <Badge className={styles[status]}>{status.replace('_', ' ')}</Badge>;
  };

  const getPriorityBadge = (priority: TicketPriority) => {
    const styles: Record<TicketPriority, string> = {
      critical: 'bg-destructive/20 text-destructive border-destructive/30',
      high: 'bg-orange-500/20 text-orange-600 border-orange-500/30',
      medium: 'bg-warning/20 text-warning border-warning/30',
      low: 'bg-muted text-muted-foreground border-border'
    };
    return <Badge className={styles[priority]}>{priority}</Badge>;
  };

  const getCategoryIcon = (category: TicketCategory) => {
    return <Badge variant="outline" className="text-xs">{category.replace('_', ' ')}</Badge>;
  };

  const getSLAStatus = (ticket: Ticket) => {
    const sla = slaConfig.find(s => s.priority === ticket.priority);
    if (!sla) return null;
    
    const createdAt = safeParseISO(getDateValue(ticket.createdAt));
    const dueDate = safeParseISO(getDateValue(ticket.dueDate));
    const now = new Date();

    if (!createdAt || !dueDate) {
      return <Badge className="bg-muted text-muted-foreground">Unknown SLA</Badge>;
    }

    const minutesElapsed = differenceInMinutes(now, createdAt);
    const isOverdue = now > dueDate;
    
    if (ticket.status === 'closed' || ticket.status === 'resolved') {
      return <Badge className="bg-success/20 text-success">Completed</Badge>;
    }
    
    if (isOverdue || ticket.slaBreached) {
      return <Badge className="bg-destructive/20 text-destructive">SLA Breached</Badge>;
    }
    
    const remainingMinutes = differenceInMinutes(dueDate, now);
    if (remainingMinutes < 60) {
      return <Badge className="bg-warning/20 text-warning">{remainingMinutes}m left</Badge>;
    }
    
    return <Badge className="bg-success/20 text-success">On Track</Badge>;
  };

  const filteredTickets = tickets.filter(ticket => {
    const matchesSearch = ticket.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         ticket.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || ticket.status === statusFilter;
    const matchesPriority = priorityFilter === 'all' || ticket.priority === priorityFilter;
    return matchesSearch && matchesStatus && matchesPriority;
  });

  const handleCreateTicket = () => {
    const newTicket: Ticket = {
      id: `TKT${String(tickets.length + 1).padStart(3, '0')}`,
      title: formData.title || '',
      description: formData.description || '',
      category: formData.category as TicketCategory || 'complaint',
      priority: formData.priority as TicketPriority || 'medium',
      status: 'open',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      dueDate: formData.dueDate || new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      assignedTo: formData.assignedTo,
      createdBy: 'Current User',
      escalationLevel: 0,
      slaBreached: false,
      comments: []
    };
    setTickets(prev => [newTicket, ...prev]);
    toast({ title: "Ticket Created", description: `Ticket ${newTicket.id} has been created.` });
    setIsCreateDialogOpen(false);
    setFormData({ title: '', description: '', category: 'complaint', priority: 'medium', dueDate: '', assignedTo: '' });
  };

  const handleStatusChange = (ticketId: string, newStatus: TicketStatus) => {
    setTickets(prev => prev.map(t => t.id === ticketId ? { ...t, status: newStatus, updatedAt: new Date().toISOString() } : t));
    if (selectedTicket?.id === ticketId) {
      setSelectedTicket(prev => prev ? { ...prev, status: newStatus } : null);
    }
    toast({ title: "Status Updated", description: `Ticket status changed to ${newStatus}.` });
  };

  const handleAddComment = () => {
    if (!selectedTicket || !newComment.trim()) return;
    
    const comment: TicketComment = {
      id: `CMT${Date.now()}`,
      ticketId: selectedTicket.id,
      author: 'Current User',
      content: newComment,
      createdAt: new Date().toISOString(),
      isInternal: false
    };
    
    setTickets(prev => prev.map(t => t.id === selectedTicket.id 
      ? { ...t, comments: [...t.comments, comment], updatedAt: new Date().toISOString() } 
      : t
    ));
    setSelectedTicket(prev => prev ? { ...prev, comments: [...prev.comments, comment] } : null);
    setNewComment('');
    toast({ title: "Comment Added", description: "Your comment has been added to the ticket." });
  };

  const handleEscalate = (ticketId: string) => {
    setTickets(prev => prev.map(t => t.id === ticketId 
      ? { ...t, escalationLevel: Math.min(t.escalationLevel + 1, 3), updatedAt: new Date().toISOString() } 
      : t
    ));
    toast({ title: "Ticket Escalated", description: "Ticket has been escalated to the next level." });
  };

  const ticketCounts = {
    all: tickets.length,
    open: tickets.filter(t => t.status === 'open').length,
    in_progress: tickets.filter(t => t.status === 'in_progress').length,
    pending: tickets.filter(t => t.status === 'pending').length,
    resolved: tickets.filter(t => t.status === 'resolved').length,
    closed: tickets.filter(t => t.status === 'closed').length,
    breached: tickets.filter(t => t.slaBreached).length
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Support"
        title="Ticket Management"
        description="Track and manage service tickets with SLA monitoring"
        icon={TicketIcon}
        actions={
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button><Plus className="h-4 w-4 mr-2" /> Create Ticket</Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Create New Ticket</DialogTitle>
              <DialogDescription>Enter the ticket details</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label>Title</Label>
                <Input value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })} placeholder="Brief description of the issue" />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} placeholder="Detailed description..." rows={3} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Category</Label>
                  <Select value={formData.category} onValueChange={(v) => setFormData({ ...formData, category: v as TicketCategory })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="complaint">Complaint</SelectItem>
                      <SelectItem value="maintenance">Maintenance</SelectItem>
                      <SelectItem value="driver_issue">Driver Issue</SelectItem>
                      <SelectItem value="vehicle_issue">Vehicle Issue</SelectItem>
                      <SelectItem value="route_issue">Route Issue</SelectItem>
                      <SelectItem value="pickup_issue">Pickup Issue</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Priority</Label>
                  <Select value={formData.priority} onValueChange={(v) => setFormData({ ...formData, priority: v as TicketPriority })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="critical">Critical</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="low">Low</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Due Date</Label>
                  <Input type="datetime-local" value={formData.dueDate} onChange={(e) => setFormData({ ...formData, dueDate: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label>Assign To</Label>
                  <Select value={formData.assignedTo || ''} onValueChange={(v) => setFormData({ ...formData, assignedTo: v })}>
                    <SelectTrigger><SelectValue placeholder="Select assignee" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Zone Supervisor">Zone Supervisor</SelectItem>
                      <SelectItem value="Fleet Manager">Fleet Manager</SelectItem>
                      <SelectItem value="Route Planner">Route Planner</SelectItem>
                      <SelectItem value="Area Manager">Area Manager</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleCreateTicket}>Create Ticket</Button>
            </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-6">
        <Card className="p-4 border-l-4 border-l-border">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total</p>
                <p className="text-2xl font-bold text-foreground">{ticketCounts.all}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-muted/30 flex items-center justify-center">
                <Tag className="h-6 w-6 text-muted-foreground" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-blue-500">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Open</p>
                <p className="text-2xl font-bold text-blue-600">{ticketCounts.open}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
                <AlertTriangle className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-primary">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">In Progress</p>
                <p className="text-2xl font-bold text-primary">{ticketCounts.in_progress}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <Clock className="h-6 w-6 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-warning">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pending</p>
                <p className="text-2xl font-bold text-warning">{ticketCounts.pending}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-warning/10 flex items-center justify-center">
                <User className="h-6 w-6 text-warning" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-success">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Resolved</p>
                <p className="text-2xl font-bold text-success">{ticketCounts.resolved}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-success/10 flex items-center justify-center">
                <CheckCircle className="h-6 w-6 text-success" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-destructive">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">SLA Breached</p>
                <p className="text-2xl font-bold text-destructive">{ticketCounts.breached}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-destructive/10 flex items-center justify-center">
                <AlertCircle className="h-6 w-6 text-destructive" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <CardContent className="p-0">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search tickets..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10" />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[150px]"><SelectValue placeholder="Status" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger className="w-[150px]"><SelectValue placeholder="Priority" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Priority</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Ticket List */}
        <Card className="lg:col-span-2 p-4">
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ticket</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>SLA</TableHead>
                  <TableHead>Assigned</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTickets.map((ticket) => (
                  <TableRow key={ticket.id} className={`cursor-pointer ${selectedTicket?.id === ticket.id ? 'bg-muted/50' : ''}`} onClick={() => setSelectedTicket(ticket)}>
                    <TableCell>
                      <div className="space-y-1">
                        <div className="font-medium text-sm">{ticket.id}</div>
                        <div className="text-sm line-clamp-1">{ticket.title}</div>
                        <div className="flex items-center gap-2">
                          {getCategoryIcon(ticket.category)}
                          {ticket.escalationLevel > 0 && <Badge variant="outline" className="text-xs bg-orange-500/10 text-orange-600">L{ticket.escalationLevel}</Badge>}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>{getPriorityBadge(ticket.priority)}</TableCell>
                    <TableCell>{getStatusBadge(ticket.status)}</TableCell>
                    <TableCell>{getSLAStatus(ticket)}</TableCell>
                    <TableCell>
                      <div className="text-sm">{ticket.assignedTo || 'Unassigned'}</div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Ticket Details */}
        <Card className="p-4">
          <CardHeader className="p-0 pb-3">
            <CardTitle className="text-lg">Ticket Details</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {selectedTicket ? (
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-semibold">{selectedTicket.id}</span>
                    {getSLAStatus(selectedTicket)}
                  </div>
                  <h3 className="font-medium">{selectedTicket.title}</h3>
                  <p className="text-sm text-muted-foreground">{selectedTicket.description}</p>
                </div>

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><span className="text-muted-foreground">Category:</span><div>{getCategoryIcon(selectedTicket.category)}</div></div>
                  <div><span className="text-muted-foreground">Priority:</span><div>{getPriorityBadge(selectedTicket.priority)}</div></div>
                  <div><span className="text-muted-foreground">Status:</span><div>{getStatusBadge(selectedTicket.status)}</div></div>
                  <div><span className="text-muted-foreground">Escalation:</span><div>Level {selectedTicket.escalationLevel}</div></div>
                </div>

                <Separator />

                <div className="space-y-2">
                  <Label>Update Status</Label>
                  <Select value={selectedTicket.status} onValueChange={(v) => handleStatusChange(selectedTicket.id, v as TicketStatus)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="open">Open</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="pending">Pending</SelectItem>
                      <SelectItem value="resolved">Resolved</SelectItem>
                      <SelectItem value="closed">Closed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Button variant="outline" className="w-full" onClick={() => handleEscalate(selectedTicket.id)} disabled={selectedTicket.escalationLevel >= 3}>
                  <ArrowUpRight className="h-4 w-4 mr-2" /> Escalate to Level {selectedTicket.escalationLevel + 1}
                </Button>

                <Separator />

                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4" />
                    <span className="font-medium">Comments ({selectedTicket.comments.length})</span>
                  </div>
                  <ScrollArea className="h-32">
                    <div className="space-y-3">
                      {selectedTicket.comments.map((comment) => (
                        <div key={comment.id} className="text-sm p-2 bg-muted/50 rounded-lg">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium">{comment.author}</span>
                            <span className="text-xs text-muted-foreground">
                              {comment.createdAt
                                ? format(parseISO(comment.createdAt), 'MMM d, HH:mm')
                                : 'Unknown'}
                            </span>
                          </div>
                          <p className="text-muted-foreground">{comment.content}</p>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                  <div className="flex gap-2">
                    <Input placeholder="Add comment..." value={newComment} onChange={(e) => setNewComment(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleAddComment()} />
                    <Button size="icon" onClick={handleAddComment}><MessageSquare className="h-4 w-4" /></Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>Select a ticket to view details</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
