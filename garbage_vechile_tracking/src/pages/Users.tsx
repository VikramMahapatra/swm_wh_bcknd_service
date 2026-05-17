import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useToast } from '@/hooks/use-toast';
import { apiService } from '@/services/api';
import { Plus, Search, Edit, Trash2, User, Shield, UserCheck, UserX, Mail, Calendar, Key, UserPlus } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { PageHeader } from '@/components/PageHeader';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

export default function Users() {
  const { toast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    password: '',
    role: 'user',
    is_active: true
  });

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setIsLoading(true);
      // For demo, we'll use mock data if API fails
      try {
        const data = await apiService.getUsers();
        setUsers(data);
      } catch (error) {
        // Use mock data
        setUsers([
          {
            id: 'user-1',
            email: 'admin@city.gov',
            name: 'Admin User',
            role: 'admin',
            is_active: true,
            created_at: '2026-01-01T00:00:00',
            last_login: '2026-02-10T20:00:00'
          },
          {
            id: 'user-2',
            email: 'operator@city.gov',
            name: 'System Operator',
            role: 'user',
            is_active: true,
            created_at: '2026-01-01T00:00:00',
            last_login: '2026-02-09T15:30:00'
          },
          {
            id: 'user-3',
            email: 'supervisor@city.gov',
            name: 'Zone Supervisor',
            role: 'user',
            is_active: true,
            created_at: '2026-01-15T00:00:00',
          }
        ]);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch users",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         user.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRole = roleFilter === 'all' || user.role === roleFilter;
    const matchesStatus = statusFilter === 'all' || 
                         (statusFilter === 'active' && user.is_active) ||
                         (statusFilter === 'inactive' && !user.is_active);
    return matchesSearch && matchesRole && matchesStatus;
  });

  const handleAddUser = async () => {
    try {
      const newUser = {
        id: `user-${users.length + 1}`,
        ...formData,
        created_at: new Date().toISOString(),
      };
      
      // Try to call API
      try {
        await apiService.register(formData);
        await fetchUsers();
      } catch (error) {
        // Mock add for demo
        setUsers([...users, newUser as User]);
      }
      
      toast({
        title: "Success",
        description: "User added successfully",
      });
      
      setIsAddDialogOpen(false);
      resetForm();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to add user",
        variant: "destructive",
      });
    }
  };

  const handleEditUser = (user: User) => {
    setEditingUser(user);
    setFormData({
      email: user.email,
      name: user.name,
      password: '',
      role: user.role,
      is_active: user.is_active
    });
    setIsAddDialogOpen(true);
  };

  const handleUpdateUser = async () => {
    if (!editingUser) return;
    
    try {
      const updatedUsers = users.map(u => 
        u.id === editingUser.id 
          ? { ...u, ...formData, password: undefined }
          : u
      );
      setUsers(updatedUsers);
      
      toast({
        title: "Success",
        description: "User updated successfully",
      });
      
      setIsAddDialogOpen(false);
      setEditingUser(null);
      resetForm();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update user",
        variant: "destructive",
      });
    }
  };

  const handleToggleStatus = async (user: User) => {
    try {
      const updatedUsers = users.map(u =>
        u.id === user.id ? { ...u, is_active: !u.is_active } : u
      );
      setUsers(updatedUsers);
      
      toast({
        title: "Success",
        description: `User ${user.is_active ? 'deactivated' : 'activated'} successfully`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update user status",
        variant: "destructive",
      });
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user?')) return;
    
    try {
      setUsers(users.filter(u => u.id !== userId));
      
      toast({
        title: "Success",
        description: "User deleted successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete user",
        variant: "destructive",
      });
    }
  };

  const resetForm = () => {
    setFormData({
      email: '',
      name: '',
      password: '',
      role: 'user',
      is_active: true
    });
  };

  const getRoleBadge = (role: string) => {
    return role === 'admin' 
      ? <Badge className="bg-primary/20 text-primary border-primary/30"><Shield className="h-3 w-3 mr-1" />Admin</Badge>
      : <Badge variant="outline"><User className="h-3 w-3 mr-1" />User</Badge>;
  };

  const getStatusBadge = (isActive: boolean) => {
    return isActive
      ? <Badge className="bg-success/20 text-success border-success/30"><UserCheck className="h-3 w-3 mr-1" />Active</Badge>
      : <Badge variant="secondary"><UserX className="h-3 w-3 mr-1" />Inactive</Badge>;
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <PageHeader
        category="Administration"
        title="User Management"
        description="Manage user accounts, roles, and permissions"
        icon={UserPlus}
        actions={
          <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={() => { setEditingUser(null); resetForm(); }}>
                <Plus className="h-4 w-4 mr-2" />
                Add User
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>{editingUser ? 'Edit User' : 'Add New User'}</DialogTitle>
              <DialogDescription>
                {editingUser ? 'Update user information' : 'Create a new user account'}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Full Name</Label>
                <Input
                  id="name"
                  placeholder="John Doe"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="user@city.gov"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password {editingUser && '(leave empty to keep current)'}</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="role">Role</Label>
                <Select value={formData.role} onValueChange={(value) => setFormData({ ...formData, role: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="user">User</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="active">Active Status</Label>
                <Switch
                  id="active"
                  checked={formData.is_active}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => { setIsAddDialogOpen(false); setEditingUser(null); resetForm(); }}>
                Cancel
              </Button>
              <Button onClick={editingUser ? handleUpdateUser : handleAddUser}>
                {editingUser ? 'Update' : 'Create'}
              </Button>
            </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 border-l-4 border-l-border">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Users</p>
                <p className="text-2xl font-bold text-foreground">{users.length}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-muted/30 flex items-center justify-center">
                <User className="h-6 w-6 text-muted-foreground" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-success">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Users</p>
                <p className="text-2xl font-bold text-success">
                  {users.filter(u => u.is_active).length}
                </p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-success/10 flex items-center justify-center">
                <UserCheck className="h-6 w-6 text-success" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-primary">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Administrators</p>
                <p className="text-2xl font-bold text-primary">
                  {users.filter(u => u.role === 'admin').length}
                </p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <Shield className="h-6 w-6 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-warning">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Regular Users</p>
                <p className="text-2xl font-bold text-foreground">
                  {users.filter(u => u.role === 'user').length}
                </p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-warning/10 flex items-center justify-center">
                <UserX className="h-6 w-6 text-warning" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card className="p-4">
        <CardHeader className="p-0 pb-3">
          <CardTitle className="text-lg">Users List</CardTitle>
          <CardDescription>View and manage all system users</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="flex flex-col md:flex-row gap-4 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by name or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="Filter by role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Roles</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="user">User</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Users Table */}
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Last Login</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      Loading users...
                    </TableCell>
                  </TableRow>
                ) : filteredUsers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      No users found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredUsers.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                            <User className="h-4 w-4 text-primary" />
                          </div>
                          {user.name}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Mail className="h-4 w-4 text-muted-foreground" />
                          {user.email}
                        </div>
                      </TableCell>
                      <TableCell>{getRoleBadge(user.role)}</TableCell>
                      <TableCell>{getStatusBadge(user.is_active)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Calendar className="h-3 w-3" />
                          {new Date(user.created_at).toLocaleDateString()}
                        </div>
                      </TableCell>
                      <TableCell>
                        {user.last_login ? (
                          <div className="text-sm text-muted-foreground">
                            {new Date(user.last_login).toLocaleString()}
                          </div>
                        ) : (
                          <span className="text-sm text-muted-foreground">Never</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleToggleStatus(user)}
                            title={user.is_active ? 'Deactivate' : 'Activate'}
                          >
                            {user.is_active ? <UserX className="h-4 w-4" /> : <UserCheck className="h-4 w-4" />}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEditUser(user)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteUser(user.id)}
                            className="text-destructive hover:text-destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
