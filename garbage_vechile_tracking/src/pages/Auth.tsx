import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, UserRole } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Truck, Mail, Lock, Shield, User } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export default function Auth() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [selectedRole, setSelectedRole] = useState<UserRole>('user');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await login(email, password, selectedRole);
      toast({
        title: "Login successful",
        description: `Welcome to Fleet Tracking System as ${selectedRole === 'admin' ? 'Administrator' : 'User'}`,
      });
      navigate('/');
    } catch (error) {
      toast({
        title: "Login failed",
        description: "Invalid credentials",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 via-background to-secondary/5 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-3 text-center">
          <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
            <Truck className="w-8 h-8 text-primary" />
          </div>
          <CardTitle className="text-2xl">Fleet Tracking System</CardTitle>
          <CardDescription>
            Municipal Garbage Truck GPS Tracking
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="admin@city.gov"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10"
                  required
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10"
                  required
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Login as</Label>
              <div className="grid grid-cols-2 gap-3">
                <Button
                  type="button"
                  variant={selectedRole === 'admin' ? 'default' : 'outline'}
                  className="h-16 flex flex-col gap-1"
                  onClick={() => setSelectedRole('admin')}
                >
                  <Shield className="h-5 w-5" />
                  <span className="text-xs">Admin</span>
                </Button>
                <Button
                  type="button"
                  variant={selectedRole === 'user' ? 'default' : 'outline'}
                  className="h-16 flex flex-col gap-1"
                  onClick={() => setSelectedRole('user')}
                >
                  <User className="h-5 w-5" />
                  <span className="text-xs">User</span>
                </Button>
              </div>
              <p className="text-xs text-muted-foreground text-center mt-1">
                {selectedRole === 'admin' ? 'Full access including Master Entries' : 'Limited access (no Master Entries)'}
              </p>
            </div>
            
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
