import { useState, useEffect } from 'react';
import { Search, ChevronDown, ChevronRight, CheckCircle, AlertTriangle, Filter } from 'lucide-react';
import { Card } from '../components/Card';
import Button from '../components/Button';
import Badge from '../components/Badge';
import { activitiesApi, type Activity } from '../lib/api';
import { cn, formatDate, formatNumber, formatCurrency } from '../lib/utils';

export default function ReviewQueue() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [filters, setFilters] = useState({
    status: 'PENDING,FLAGGED',
    is_suspicious: '',
    search: '',
    source_type: '',
  });
  const [showFilters, setShowFilters] = useState(false);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    fetchActivities();
  }, [filters]);

  const fetchActivities = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (filters.status) {
        const statuses = filters.status.split(',');
        statuses.forEach(s => params.status = s); // DRF accepts multiple status params
      }
      if (filters.is_suspicious) params.is_suspicious = filters.is_suspicious;
      if (filters.search) params.search = filters.search;
      if (filters.source_type) params.source_type = filters.source_type;

      const response = await activitiesApi.list(params);
      setActivities(response.data.results);
      setTotalCount(response.data.count);
    } catch (error) {
      console.error('Failed to fetch activities:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: number) => {
    try {
      await activitiesApi.approve(id);
      fetchActivities();
    } catch (error) {
      console.error('Failed to approve activity:', error);
    }
  };

  const handleBulkApproveClean = async () => {
    const cleanActivities = activities.filter(a =>
      !a.is_suspicious && (a.status === 'PENDING' || a.status === 'FLAGGED')
    );

    if (cleanActivities.length === 0) {
      alert('No clean activities to approve');
      return;
    }

    if (!confirm(`Approve ${cleanActivities.length} clean (non-flagged) activities?`)) {
      return;
    }

    try {
      await Promise.all(cleanActivities.map(a => activitiesApi.approve(a.id)));
      fetchActivities();
    } catch (error) {
      console.error('Failed to bulk approve:', error);
      alert('Some activities failed to approve. Check console for details.');
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      PENDING: { variant: 'default', label: 'Pending' },
      FLAGGED: { variant: 'warning', label: 'Flagged' },
      APPROVED: { variant: 'success', label: 'Approved' },
      LOCKED: { variant: 'info', label: 'Locked' },
      INVALIDATED: { variant: 'danger', label: 'Invalidated' },
    };
    const config = variants[status] || variants.PENDING;
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  const getScopeBadge = (scope: number) => {
    const colors: Record<number, string> = {
      1: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
      2: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
      3: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
    };
    return (
      <Badge className={colors[scope] || ''} size="sm">
        Scope {scope}
      </Badge>
    );
  };

  const renderDetailRow = (activity: Activity) => {
    if (activity.sap_detail) {
      const d = activity.sap_detail;
      return (
        <div className="space-y-3">
          <div className="font-semibold text-sm text-brand-600">SAP Material Details</div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Material Number:</span>{' '}
              <span className="font-medium">{d.material_number}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Material Desc:</span>{' '}
              <span className="font-medium">{d.material_desc}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Material Group:</span>{' '}
              <span className="font-medium">{d.material_group || 'N/A'}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Plant Code:</span>{' '}
              <span className="font-medium">{d.plant_code}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Movement Type:</span>{' '}
              <span className="font-medium">{d.movement_type}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Classification:</span>{' '}
              <Badge size="sm">{d.classification_method}</Badge>
            </div>
            <div>
              <span className="text-muted-foreground">Raw Quantity:</span>{' '}
              <span className="font-medium">{formatNumber(d.quantity_raw)} {d.unit_raw}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Normalized:</span>{' '}
              <span className="font-medium">{formatNumber(d.quantity_normalized)} {d.unit_normalized}</span>
            </div>
            {d.conversion_note && (
              <div>
                <span className="text-muted-foreground">Conversion:</span>{' '}
                <span className="font-medium text-xs">{d.conversion_note}</span>
              </div>
            )}
          </div>
        </div>
      );
    }
    if (activity.utility_detail) {
      const d = activity.utility_detail;
      return (
        <div className="space-y-3">
          <div className="font-semibold text-sm text-brand-600">Utility Details</div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Service Number:</span>{' '}
              <span className="font-medium">{d.service_number}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Tariff Category:</span>{' '}
              <span className="font-medium">{d.tariff_category}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Unit:</span>{' '}
              <span className="font-medium">{d.unit_raw}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Consumption:</span>{' '}
              <span className="font-medium">{formatNumber(d.kwh_consumed)} kWh</span>
            </div>
            <div>
              <span className="text-muted-foreground">Billing Amount:</span>{' '}
              <span className="font-medium">{formatCurrency(d.billing_amount_inr)}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Grid EF:</span>{' '}
              <span className="font-medium text-xs">{d.grid_emission_factor} kgCO₂e/kWh</span>
            </div>
          </div>
        </div>
      );
    }
    if (activity.travel_detail) {
      const d = activity.travel_detail;
      return (
        <div className="space-y-3">
          <div className="font-semibold text-sm text-brand-600">Travel Expense Details</div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Trip ID:</span>{' '}
              <span className="font-medium">{d.trip_id}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Employee:</span>{' '}
              <span className="font-medium">{d.employee_id}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Mode:</span>{' '}
              <Badge size="sm">{d.mode}</Badge>
            </div>
            {d.department && (
              <div>
                <span className="text-muted-foreground">Department:</span>{' '}
                <span className="font-medium">{d.department}</span>
              </div>
            )}
            {d.cost_center && (
              <div>
                <span className="text-muted-foreground">Cost Center:</span>{' '}
                <span className="font-medium">{d.cost_center}</span>
              </div>
            )}
            {d.origin && d.destination && (
              <div>
                <span className="text-muted-foreground">Route:</span>{' '}
                <span className="font-medium">{d.origin} → {d.destination}</span>
              </div>
            )}
            {d.distance_km && (
              <div>
                <span className="text-muted-foreground">Distance:</span>{' '}
                <span className="font-medium">{formatNumber(d.distance_km)} km</span>
              </div>
            )}
            {d.cabin_class && (
              <div>
                <span className="text-muted-foreground">Cabin Class:</span>{' '}
                <span className="font-medium">{d.cabin_class}</span>
              </div>
            )}
            {d.nights && (
              <div>
                <span className="text-muted-foreground">Nights:</span>{' '}
                <span className="font-medium">{d.nights}</span>
              </div>
            )}
          </div>

          {/* Currency/FX Section */}
          <div className="mt-4 pt-4 border-t">
            <div className="font-semibold text-sm text-purple-600 mb-2">Currency & FX Details</div>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Original Amount:</span>{' '}
                <span className="font-medium">{formatCurrency(d.amount_raw, d.currency)}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Amount in INR:</span>{' '}
                <span className="font-medium">{d.amount_inr ? formatCurrency(d.amount_inr, 'INR') : 'N/A'}</span>
              </div>
              {(d as any).fx_rate_used && (
                <>
                  <div>
                    <span className="text-muted-foreground">FX Rate:</span>{' '}
                    <span className="font-medium">1 {d.currency} = {(d as any).fx_rate_used} INR</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">FX Date:</span>{' '}
                    <span className="font-medium">{(d as any).fx_rate_date || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">FX Source:</span>{' '}
                    <span className="font-medium text-xs">{(d as any).fx_source || 'N/A'}</span>
                  </div>
                  {(d as any).fx_note && (
                    <div className="col-span-3">
                      <span className="text-muted-foreground">FX Note:</span>{' '}
                      <span className="font-medium text-xs">{(d as any).fx_note}</span>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight mb-2">Review Queue</h1>
          <p className="text-muted-foreground text-lg">
            {totalCount} activities • Review and approve emissions data
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Button
            variant="primary"
            onClick={handleBulkApproveClean}
            disabled={activities.filter(a => !a.is_suspicious && (a.status === 'PENDING' || a.status === 'FLAGGED')).length === 0}
            className="gap-2"
          >
            <CheckCircle className="h-4 w-4" />
            Approve All Clean
          </Button>
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className="gap-2"
          >
            <Filter className="h-4 w-4" />
            Filters
          </Button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <Card className="animate-slide-in">
          <div className="p-6">
            <div className="grid grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Status</label>
                <select
                  value={filters.status}
                  onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background"
                >
                  <option value="">All</option>
                  <option value="PENDING,FLAGGED">Pending & Flagged</option>
                  <option value="PENDING">Pending Only</option>
                  <option value="FLAGGED">Flagged Only</option>
                  <option value="APPROVED">Approved</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Suspicious</label>
                <select
                  value={filters.is_suspicious}
                  onChange={(e) => setFilters({ ...filters, is_suspicious: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background"
                >
                  <option value="">All</option>
                  <option value="true">Flagged Only</option>
                  <option value="false">Clean Only</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Source Type</label>
                <select
                  value={filters.source_type}
                  onChange={(e) => setFilters({ ...filters, source_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background"
                >
                  <option value="">All</option>
                  <option value="SAP">SAP</option>
                  <option value="UTILITY">Utility</option>
                  <option value="TRAVEL_CONCUR">Travel (Concur)</option>
                  <option value="TRAVEL_NAVAN">Travel (Navan)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Search</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Material, service no..."
                    value={filters.search}
                    onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                    className="w-full pl-9 pr-3 py-2 rounded-lg border border-input bg-background"
                  />
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Activities Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider w-8"></th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Scope</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Category</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Period</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Facility</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Source</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">
                    Loading activities...
                  </td>
                </tr>
              ) : activities.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">
                    No activities found
                  </td>
                </tr>
              ) : (
                activities.map((activity) => (
                  <>
                    <tr
                      key={activity.id}
                      className={cn(
                        'hover:bg-muted/50 transition-colors cursor-pointer',
                        activity.is_suspicious && 'bg-yellow-50/50 dark:bg-yellow-900/5'
                      )}
                      onClick={() => setExpandedRow(expandedRow === activity.id ? null : activity.id)}
                    >
                      <td className="px-4 py-4">
                        {expandedRow === activity.id ? (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        )}
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center space-x-2">
                          {getStatusBadge(activity.status)}
                          {activity.is_suspicious && (
                            <AlertTriangle className="h-4 w-4 text-yellow-600" />
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-4">{getScopeBadge(activity.scope)}</td>
                      <td className="px-4 py-4">
                        <span className="text-sm font-medium">{activity.category}</span>
                      </td>
                      <td className="px-4 py-4 text-sm">{formatDate(activity.period_end)}</td>
                      <td className="px-4 py-4 text-sm text-muted-foreground">
                        {activity.facility_name || 'N/A'}
                      </td>
                      <td className="px-4 py-4">
                        <Badge size="sm" variant="default">{activity.source_type}</Badge>
                      </td>
                      <td className="px-4 py-4">
                        {(activity.status === 'PENDING' || activity.status === 'FLAGGED') && (
                          <Button
                            size="sm"
                            variant="primary"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleApprove(activity.id);
                            }}
                            className="gap-1"
                          >
                            <CheckCircle className="h-3 w-3" />
                            Approve
                          </Button>
                        )}
                      </td>
                    </tr>
                    {expandedRow === activity.id && (
                      <tr className="bg-muted/30">
                        <td colSpan={8} className="px-4 py-6">
                          <div className="space-y-4">
                            {activity.flag_reason && (
                              <div className="p-3 bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-900 rounded-lg">
                                <div className="flex items-start space-x-2">
                                  <AlertTriangle className="h-4 w-4 text-yellow-600 flex-shrink-0 mt-0.5" />
                                  <div>
                                    <div className="text-sm font-medium text-yellow-900 dark:text-yellow-100 mb-1">
                                      Suspicious Flags
                                    </div>
                                    <div className="flex flex-wrap gap-1">
                                      {activity.flag_reason.split('|').map((flag) => (
                                        <Badge key={flag} variant="warning" size="sm">
                                          {flag.replace(/_/g, ' ')}
                                        </Badge>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}
                            <div className="p-4 bg-background border rounded-lg">
                              {renderDetailRow(activity)}
                            </div>
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
      </Card>
    </div>
  );
}
