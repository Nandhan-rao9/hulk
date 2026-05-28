import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, FileText, TrendingUp, Zap, Plane, Building2, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import Badge from '../components/Badge';
import Button from '../components/Button';
import { sourceFilesApi, type FileActivitiesResponse, type FileSummaryResponse } from '../lib/api';
import { formatNumber, formatDate } from '../lib/utils';

export default function FileDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<FileActivitiesResponse | null>(null);
  const [summary, setSummary] = useState<FileSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    if (!id) return;

    setLoading(true);
    setError(null);

    try {
      const [activitiesRes, summaryRes] = await Promise.all([
        sourceFilesApi.getActivities(parseInt(id)),
        sourceFilesApi.getSummary(parseInt(id))
      ]);
      setData(activitiesRes.data);
      setSummary(summaryRes.data);
    } catch (err: any) {
      console.error('FileDetail error:', err);
      const errorDetail = err.response?.data?.detail || err.message || 'Failed to load file details';
      setError(errorDetail);
    } finally {
      setLoading(false);
    }
  };

  const getSourceIcon = (sourceType: string) => {
    if (sourceType === 'SAP') return <Building2 className="h-5 w-5" />;
    if (sourceType === 'UTILITY') return <Zap className="h-5 w-5" />;
    if (sourceType.startsWith('TRAVEL')) return <Plane className="h-5 w-5" />;
    return <FileText className="h-5 w-5" />;
  };

  const getScopeColor = (scope: number) => {
    if (scope === 1) return 'text-red-600';
    if (scope === 2) return 'text-orange-600';
    return 'text-blue-600';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600 mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading file details...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <Card className="border-destructive max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-6xl mb-4">❌</div>
              <h2 className="text-xl font-bold mb-2">Error Loading File</h2>
              <p className="text-muted-foreground mb-4">{error || 'File not found'}</p>
              <Button onClick={() => navigate('/files')}>Back to Files</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const totalEmissions = data.activities.reduce((sum, a) => sum + a.emissions_kgco2e, 0);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" onClick={() => navigate('/files')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Files
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{data.filename}</h1>
            <div className="flex items-center space-x-2 mt-1">
              <Badge variant="info">{data.source_type}</Badge>
              <span className="text-sm text-muted-foreground">
                {data.total_approved} approved activities
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Status Summary Cards */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Approved</p>
                  <p className="text-3xl font-bold text-brand-600">{summary.status_counts.APPROVED || 0}</p>
                </div>
                <div className="h-12 w-12 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                  {getSourceIcon(data.source_type)}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div>
                <p className="text-sm text-muted-foreground">Pending</p>
                <p className="text-3xl font-bold text-yellow-600">{summary.status_counts.PENDING || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div>
                <p className="text-sm text-muted-foreground">Flagged</p>
                <p className="text-3xl font-bold text-orange-600">{summary.status_counts.FLAGGED || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div>
                <p className="text-sm text-muted-foreground">Total Emissions</p>
                <p className="text-2xl font-bold">{formatNumber(summary.emissions_total_kgco2e)}</p>
                <p className="text-xs text-muted-foreground mt-1">kg CO₂e</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Activities Table */}
      <Card>
        <CardHeader>
          <CardTitle>Approved Activities</CardTitle>
          <CardDescription>
            Showing all approved activities from this file with their key metrics
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b text-left text-sm text-muted-foreground">
                  <th className="pb-3 font-medium">Date</th>
                  <th className="pb-3 font-medium">Scope</th>
                  <th className="pb-3 font-medium">Category</th>
                  <th className="pb-3 font-medium">Facility/Detail</th>
                  <th className="pb-3 font-medium text-right">Metric</th>
                  <th className="pb-3 font-medium text-right">Emissions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.activities.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12">
                      <div className="text-center">
                        <div className="flex items-center justify-center mb-4">
                          <AlertCircle className="h-12 w-12 text-muted-foreground" />
                        </div>
                        <h3 className="text-lg font-semibold mb-2">No Approved Activities Yet</h3>
                        <p className="text-sm text-muted-foreground mb-4">
                          This file has {summary?.status_counts.PENDING || 0} pending and {summary?.status_counts.FLAGGED || 0} flagged activities.
                        </p>
                        <Link to="/review">
                          <Button variant="outline">
                            Go to Review Queue
                          </Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ) : (
                  data.activities.map((activity) => (
                    <tr key={activity.id} className="hover:bg-muted/50 transition-colors">
                      <td className="py-3 text-sm">
                        {formatDate(activity.period_end)}
                      </td>
                      <td className="py-3">
                        <span className={`text-sm font-medium ${getScopeColor(activity.scope)}`}>
                          Scope {activity.scope}
                        </span>
                      </td>
                      <td className="py-3">
                        <Badge variant="default" size="sm">
                          {activity.category}
                        </Badge>
                      </td>
                      <td className="py-3 text-sm">
                        {activity.facility_name || activity.material || activity.service_number || activity.employee_id || '—'}
                      </td>
                      <td className="py-3 text-sm text-right font-mono">
                        <div>{formatNumber(activity.metric_value)} {activity.metric_unit}</div>
                        <div className="text-xs text-muted-foreground">{activity.metric_label}</div>
                      </td>
                      <td className="py-3 text-sm text-right font-mono">
                        {formatNumber(activity.emissions_kgco2e)} kg CO₂e
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
