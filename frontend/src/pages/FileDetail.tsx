import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, FileText, Zap, Plane, Building2, AlertCircle, ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import Badge from '../components/Badge';
import Button from '../components/Button';
import { sourceFilesApi, activitiesApi, type FileActivitiesResponse, type FileSummaryResponse } from '../lib/api';
import { formatNumber, formatDate } from '../lib/utils';
import { useAuth } from '../contexts/AuthContext';

export default function FileDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const [data, setData] = useState<FileActivitiesResponse | null>(null);
  const [summary, setSummary] = useState<FileSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  // Flag dialog state
  const [flagDialogActivity, setFlagDialogActivity] = useState<number | null>(null);
  const [flagReason, setFlagReason] = useState('');
  const [flagNote, setFlagNote] = useState('');

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


  const handleFlag = async () => {
    if (!flagDialogActivity || !flagReason) return;

    try {
      await activitiesApi.flag(flagDialogActivity, flagReason, flagNote);
      setFlagDialogActivity(null);
      setFlagReason('');
      setFlagNote('');
      // Reload data to refresh status
      loadData();
      alert('Activity flagged successfully. It will now appear in the Review Queue.');
    } catch (error: any) {
      console.error('Failed to flag activity:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to flag activity';
      alert(errorMsg);
    }
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
                  <th className="pb-3 font-medium w-8"></th>
                  <th className="pb-3 font-medium">Date</th>
                  <th className="pb-3 font-medium">Category</th>
                  <th className="pb-3 font-medium">Facility/Detail</th>
                  <th className="pb-3 font-medium text-right">Metric</th>
                  <th className="pb-3 font-medium text-right">Emissions</th>
                  <th className="pb-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.activities.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12">
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
                    <>
                      <tr
                        key={activity.id}
                        className="hover:bg-muted/50 transition-colors cursor-pointer"
                        onClick={() => setExpandedRow(expandedRow === activity.id ? null : activity.id)}
                      >
                        <td className="py-3 px-2">
                          {expandedRow === activity.id ? (
                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                          )}
                        </td>
                        <td className="py-3 text-sm">
                          {formatDate(activity.period_end)}
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
                        <td className="py-3 text-right">
                          {isAdmin && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={(e) => {
                                e.stopPropagation();
                                setFlagDialogActivity(activity.id);
                              }}
                              className="gap-1 text-yellow-600 border-yellow-300 hover:bg-yellow-50 dark:hover:bg-yellow-900/10"
                            >
                              <AlertTriangle className="h-3 w-3" />
                              Flag
                            </Button>
                          )}
                        </td>
                      </tr>

                      {/* Expanded Detail Row */}
                      {expandedRow === activity.id && (
                        <tr className="bg-muted/30">
                          <td colSpan={7} className="px-4 py-4">
                            <div className="space-y-3">
                              <div className="text-sm font-medium text-muted-foreground mb-2">
                                Activity Details
                              </div>
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                                <div>
                                  <span className="text-muted-foreground">Activity ID:</span>{' '}
                                  <span className="font-medium">#{activity.id}</span>
                                </div>
                                {activity.material && (
                                  <div>
                                    <span className="text-muted-foreground">Material:</span>{' '}
                                    <span className="font-medium">{activity.material}</span>
                                  </div>
                                )}
                                {activity.service_number && (
                                  <div>
                                    <span className="text-muted-foreground">Service #:</span>{' '}
                                    <span className="font-medium">{activity.service_number}</span>
                                  </div>
                                )}
                                {activity.employee_id && (
                                  <div>
                                    <span className="text-muted-foreground">Employee:</span>{' '}
                                    <span className="font-medium">{activity.employee_id}</span>
                                  </div>
                                )}
                                {activity.mode && (
                                  <div>
                                    <span className="text-muted-foreground">Travel Mode:</span>{' '}
                                    <span className="font-medium">{activity.mode}</span>
                                  </div>
                                )}
                                {activity.cabin_class && (
                                  <div>
                                    <span className="text-muted-foreground">Cabin Class:</span>{' '}
                                    <Badge size="sm">{activity.cabin_class}</Badge>
                                  </div>
                                )}
                                {activity.distance_km && (
                                  <div>
                                    <span className="text-muted-foreground">Distance:</span>{' '}
                                    <span className="font-medium">{formatNumber(activity.distance_km)} km</span>
                                  </div>
                                )}
                                {activity.nights && (
                                  <div>
                                    <span className="text-muted-foreground">Nights:</span>{' '}
                                    <span className="font-medium">{activity.nights}</span>
                                  </div>
                                )}
                                <div>
                                  <span className="text-muted-foreground">Metric:</span>{' '}
                                  <span className="font-medium">{formatNumber(activity.metric_value)} {activity.metric_unit}</span>
                                </div>
                                <div>
                                  <span className="text-muted-foreground">Emissions:</span>{' '}
                                  <span className="font-medium">{formatNumber(activity.emissions_kgco2e)} kg CO₂e</span>
                                </div>
                              </div>
                              {isAdmin && (
                                <div className="pt-2 border-t">
                                  <p className="text-xs text-muted-foreground italic">
                                    Click "Flag" if you notice an error in this approved activity. It will be moved back to the Review Queue for correction.
                                  </p>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Flag Dialog Modal */}
      {flagDialogActivity && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setFlagDialogActivity(null)}>
          <div className="w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-bold mb-4">Flag Approved Activity</h2>
                <p className="text-sm text-muted-foreground mb-4">
                  This activity will be moved back to the Review Queue and its approval will be revoked.
                </p>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Flag Reason <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={flagReason}
                      onChange={(e) => setFlagReason(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-brand-500"
                    >
                      <option value="">Select reason...</option>
                      <option value="incorrect_amount">Incorrect Amount</option>
                      <option value="incorrect_date">Incorrect Date</option>
                      <option value="incorrect_plant">Incorrect Plant Code</option>
                      <option value="duplicate_suspected">Suspected Duplicate</option>
                      <option value="missing_documentation">Missing Documentation</option>
                      <option value="unusual_quantity">Unusual Quantity</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Details / Notes *</label>
                    <textarea
                      value={flagNote}
                      onChange={(e) => setFlagNote(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-brand-500"
                      rows={3}
                      placeholder="Explain what needs to be corrected..."
                      required
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Required: Explain what's wrong so the reviewer knows what to fix.
                    </p>
                  </div>
                  <div className="flex justify-end space-x-2 pt-2">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setFlagDialogActivity(null);
                        setFlagReason('');
                        setFlagNote('');
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      onClick={handleFlag}
                      disabled={!flagReason || !flagNote.trim()}
                      className="gap-2"
                    >
                      <AlertTriangle className="h-4 w-4" />
                      Flag Activity
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
