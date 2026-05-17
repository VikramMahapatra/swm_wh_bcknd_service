import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Twitter, 
  RefreshCw, 
  Search, 
  MessageCircle, 
  Heart, 
  Repeat2, 
  ExternalLink,
  AlertCircle,
  Clock,
  TrendingUp,
  Filter,
  Download,
  Settings
} from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/PageHeader';

// Mock tweet data - in production, this would come from Twitter API
const mockTweets = [
  {
    id: '1',
    author: '@citizen_pune',
    authorName: 'Pune Citizen',
    avatar: 'PC',
    content: '@MunicipalGC Garbage truck hasn\'t arrived in Kharadi sector 5 for 2 days now. Please look into this urgently!',
    timestamp: '2024-01-15T09:30:00Z',
    likes: 45,
    retweets: 12,
    replies: 8,
    sentiment: 'negative',
    category: 'complaint',
    location: 'Kharadi, Sector 5'
  },
  {
    id: '2',
    author: '@green_warrior',
    authorName: 'Green Warrior',
    avatar: 'GW',
    content: '@MunicipalGC Thank you for the quick response yesterday! The new collection schedule is working great in our area.',
    timestamp: '2024-01-15T08:15:00Z',
    likes: 89,
    retweets: 23,
    replies: 5,
    sentiment: 'positive',
    category: 'appreciation',
    location: 'Viman Nagar'
  },
  {
    id: '3',
    author: '@resident_wakad',
    authorName: 'Wakad Resident',
    avatar: 'WR',
    content: '@MunicipalGC When will the new waste collection points be set up in Wakad? We\'ve been waiting for months.',
    timestamp: '2024-01-15T07:45:00Z',
    likes: 67,
    retweets: 34,
    replies: 12,
    sentiment: 'neutral',
    category: 'inquiry',
    location: 'Wakad'
  },
  {
    id: '4',
    author: '@clean_city',
    authorName: 'Clean City Initiative',
    avatar: 'CC',
    content: '@MunicipalGC Missed garbage pickup at Hinjewadi Phase 2 near IT Park entrance. Immediate attention needed! #SwachhBharat',
    timestamp: '2024-01-15T06:30:00Z',
    likes: 156,
    retweets: 78,
    replies: 23,
    sentiment: 'negative',
    category: 'complaint',
    location: 'Hinjewadi Phase 2'
  },
  {
    id: '5',
    author: '@eco_activist',
    authorName: 'Eco Activist',
    avatar: 'EA',
    content: '@MunicipalGC The new electric garbage trucks are amazing! Great initiative towards sustainability. 🌱',
    timestamp: '2024-01-14T18:20:00Z',
    likes: 234,
    retweets: 89,
    replies: 15,
    sentiment: 'positive',
    category: 'appreciation',
    location: 'Pune'
  },
  {
    id: '6',
    author: '@daily_observer',
    authorName: 'Daily Observer',
    avatar: 'DO',
    content: '@MunicipalGC Garbage collection truck MH12AB1234 was seen dumping waste illegally near river bank. Please investigate.',
    timestamp: '2024-01-14T16:45:00Z',
    likes: 312,
    retweets: 145,
    replies: 56,
    sentiment: 'negative',
    category: 'violation',
    location: 'Mula-Mutha Riverbank'
  },
  {
    id: '7',
    author: '@society_admin',
    authorName: 'Society Admin',
    avatar: 'SA',
    content: '@MunicipalGC Request to add our new society "Green Meadows" to the collection route. Located near Baner bypass.',
    timestamp: '2024-01-14T14:10:00Z',
    likes: 23,
    retweets: 5,
    replies: 3,
    sentiment: 'neutral',
    category: 'request',
    location: 'Baner'
  },
  {
    id: '8',
    author: '@health_dept',
    authorName: 'Health Department',
    avatar: 'HD',
    content: '@MunicipalGC Excellent coordination during the festival cleanup drive. The city looks spotless! 👏',
    timestamp: '2024-01-14T12:00:00Z',
    likes: 456,
    retweets: 123,
    replies: 34,
    sentiment: 'positive',
    category: 'appreciation',
    location: 'Pune City'
  }
];

const getSentimentColor = (sentiment: string) => {
  switch (sentiment) {
    case 'positive': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
    case 'negative': return 'bg-red-500/20 text-red-400 border-red-500/30';
    default: return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
  }
};

const getCategoryColor = (category: string) => {
  switch (category) {
    case 'complaint': return 'bg-red-500/20 text-red-400';
    case 'appreciation': return 'bg-emerald-500/20 text-emerald-400';
    case 'inquiry': return 'bg-blue-500/20 text-blue-400';
    case 'violation': return 'bg-orange-500/20 text-orange-400';
    case 'request': return 'bg-purple-500/20 text-purple-400';
    default: return 'bg-muted text-muted-foreground';
  }
};

const formatTimeAgo = (timestamp: string) => {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHrs / 24);
  
  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHrs > 0) return `${diffHrs}h ago`;
  return 'Just now';
};

export default function TwitterMentions() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [sentimentFilter, setSentimentFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [trackedHandle, setTrackedHandle] = useState('@MunicipalGC');

  useEffect(() => {
    // Load tracked handle from localStorage
    const savedHandle = localStorage.getItem('twitterTrackedHandle');
    if (savedHandle) {
      setTrackedHandle(savedHandle);
    }
  }, []);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 2000);
  };

  const filteredTweets = mockTweets.filter(tweet => {
    const matchesSearch = tweet.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         tweet.author.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         tweet.location?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSentiment = sentimentFilter === 'all' || tweet.sentiment === sentimentFilter;
    const matchesCategory = categoryFilter === 'all' || tweet.category === categoryFilter;
    return matchesSearch && matchesSentiment && matchesCategory;
  });

  const stats = {
    total: mockTweets.length,
    positive: mockTweets.filter(t => t.sentiment === 'positive').length,
    negative: mockTweets.filter(t => t.sentiment === 'negative').length,
    neutral: mockTweets.filter(t => t.sentiment === 'neutral').length,
    complaints: mockTweets.filter(t => t.category === 'complaint').length,
  };

  const exportToCSV = () => {
    const headers = ['Author', 'Content', 'Timestamp', 'Sentiment', 'Category', 'Location', 'Likes', 'Retweets'];
    const rows = filteredTweets.map(t => [
      t.author, 
      `"${t.content.replace(/"/g, '""')}"`, 
      t.timestamp, 
      t.sentiment, 
      t.category, 
      t.location || '',
      t.likes,
      t.retweets
    ]);
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `twitter_mentions_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <PageHeader
        category="Social Media"
        title="Twitter Mentions"
        description={`Tracking mentions of ${trackedHandle}`}
        icon={Twitter}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => navigate('/settings')}>
              <Settings className="h-4 w-4 mr-2" />
              Configure Handle
            </Button>
            <Button variant="outline" size="sm" onClick={exportToCSV}>
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
            <Button onClick={handleRefresh} disabled={isRefreshing}>
              <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </>
        }
      />

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="p-4 border-l-4 border-l-[#1DA1F2]">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Mentions</p>
                <p className="text-2xl font-bold text-foreground">{stats.total}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-[#1DA1F2]/10 flex items-center justify-center">
                <MessageCircle className="h-6 w-6 text-[#1DA1F2]" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-emerald-500">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Positive</p>
                <p className="text-2xl font-bold text-emerald-400">{stats.positive}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                <TrendingUp className="h-6 w-6 text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-red-500">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Negative</p>
                <p className="text-2xl font-bold text-red-400">{stats.negative}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-red-500/10 flex items-center justify-center">
                <AlertCircle className="h-6 w-6 text-red-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-amber-500">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Neutral</p>
                <p className="text-2xl font-bold text-amber-400">{stats.neutral}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-amber-500/10 flex items-center justify-center">
                <Clock className="h-6 w-6 text-amber-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-orange-500">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Complaints</p>
                <p className="text-2xl font-bold text-orange-400">{stats.complaints}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-orange-500/10 flex items-center justify-center">
                <Filter className="h-6 w-6 text-orange-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="bg-card/50 border-border/50">
        <CardContent className="pt-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search tweets, authors, or locations..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={sentimentFilter} onValueChange={setSentimentFilter}>
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="Sentiment" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sentiments</SelectItem>
                <SelectItem value="positive">Positive</SelectItem>
                <SelectItem value="negative">Negative</SelectItem>
                <SelectItem value="neutral">Neutral</SelectItem>
              </SelectContent>
            </Select>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                <SelectItem value="complaint">Complaints</SelectItem>
                <SelectItem value="appreciation">Appreciation</SelectItem>
                <SelectItem value="inquiry">Inquiries</SelectItem>
                <SelectItem value="violation">Violations</SelectItem>
                <SelectItem value="request">Requests</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Tweets List */}
      <Tabs defaultValue="all" className="space-y-4">
        <TabsList className="bg-muted/50">
          <TabsTrigger value="all">All Mentions</TabsTrigger>
          <TabsTrigger value="urgent">Urgent</TabsTrigger>
          <TabsTrigger value="actionable">Actionable</TabsTrigger>
        </TabsList>

        <TabsContent value="all">
          <ScrollArea className="h-[600px]">
            <div className="space-y-4 pr-4">
              {filteredTweets.map((tweet) => (
                <Card key={tweet.id} className="bg-card/50 border-border/50 hover:bg-card/80 transition-colors">
                  <CardContent className="pt-4">
                    <div className="flex gap-4">
                      {/* Avatar */}
                      <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold">
                        {tweet.avatar}
                      </div>
                      
                      {/* Content */}
                      <div className="flex-1 space-y-2">
                        <div className="flex items-start justify-between">
                          <div>
                            <span className="font-semibold">{tweet.authorName}</span>
                            <span className="text-muted-foreground ml-2">{tweet.author}</span>
                            <span className="text-muted-foreground mx-2">·</span>
                            <span className="text-muted-foreground text-sm">{formatTimeAgo(tweet.timestamp)}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className={getSentimentColor(tweet.sentiment)}>
                              {tweet.sentiment}
                            </Badge>
                            <Badge variant="secondary" className={getCategoryColor(tweet.category)}>
                              {tweet.category}
                            </Badge>
                          </div>
                        </div>
                        
                        <p className="text-foreground">{tweet.content}</p>
                        
                        {tweet.location && (
                          <p className="text-sm text-muted-foreground">📍 {tweet.location}</p>
                        )}
                        
                        {/* Engagement */}
                        <div className="flex items-center gap-6 pt-2">
                          <button className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors">
                            <MessageCircle className="h-4 w-4" />
                            <span className="text-sm">{tweet.replies}</span>
                          </button>
                          <button className="flex items-center gap-2 text-muted-foreground hover:text-emerald-400 transition-colors">
                            <Repeat2 className="h-4 w-4" />
                            <span className="text-sm">{tweet.retweets}</span>
                          </button>
                          <button className="flex items-center gap-2 text-muted-foreground hover:text-red-400 transition-colors">
                            <Heart className="h-4 w-4" />
                            <span className="text-sm">{tweet.likes}</span>
                          </button>
                          <button className="flex items-center gap-2 text-muted-foreground hover:text-[#1DA1F2] transition-colors ml-auto">
                            <ExternalLink className="h-4 w-4" />
                            <span className="text-sm">View on X</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="urgent">
          <ScrollArea className="h-[600px]">
            <div className="space-y-4 pr-4">
              {filteredTweets.filter(t => t.sentiment === 'negative' || t.category === 'violation').map((tweet) => (
                <Card key={tweet.id} className="bg-card/50 border-red-500/30 hover:bg-card/80 transition-colors">
                  <CardContent className="pt-4">
                    <div className="flex gap-4">
                      <div className="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center text-red-400 font-bold">
                        {tweet.avatar}
                      </div>
                      <div className="flex-1 space-y-2">
                        <div className="flex items-start justify-between">
                          <div>
                            <span className="font-semibold">{tweet.authorName}</span>
                            <span className="text-muted-foreground ml-2">{tweet.author}</span>
                            <span className="text-muted-foreground mx-2">·</span>
                            <span className="text-muted-foreground text-sm">{formatTimeAgo(tweet.timestamp)}</span>
                          </div>
                          <Badge variant="destructive">Urgent</Badge>
                        </div>
                        <p className="text-foreground">{tweet.content}</p>
                        {tweet.location && (
                          <p className="text-sm text-muted-foreground">📍 {tweet.location}</p>
                        )}
                        <div className="flex gap-2 pt-2">
                          <Button size="sm" variant="destructive">Take Action</Button>
                          <Button size="sm" variant="outline">Assign</Button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="actionable">
          <ScrollArea className="h-[600px]">
            <div className="space-y-4 pr-4">
              {filteredTweets.filter(t => ['complaint', 'request', 'violation'].includes(t.category)).map((tweet) => (
                <Card key={tweet.id} className="bg-card/50 border-amber-500/30 hover:bg-card/80 transition-colors">
                  <CardContent className="pt-4">
                    <div className="flex gap-4">
                      <div className="w-12 h-12 rounded-full bg-amber-500/20 flex items-center justify-center text-amber-400 font-bold">
                        {tweet.avatar}
                      </div>
                      <div className="flex-1 space-y-2">
                        <div className="flex items-start justify-between">
                          <div>
                            <span className="font-semibold">{tweet.authorName}</span>
                            <span className="text-muted-foreground ml-2">{tweet.author}</span>
                          </div>
                          <Badge variant="outline" className={getCategoryColor(tweet.category)}>
                            {tweet.category}
                          </Badge>
                        </div>
                        <p className="text-foreground">{tweet.content}</p>
                        {tweet.location && (
                          <p className="text-sm text-muted-foreground">📍 {tweet.location}</p>
                        )}
                        <div className="flex gap-2 pt-2">
                          <Button size="sm">Respond</Button>
                          <Button size="sm" variant="outline">Create Ticket</Button>
                          <Button size="sm" variant="ghost">Dismiss</Button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  );
}
