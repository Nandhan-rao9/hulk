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
      return (
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Material:</span>{' '}
            <span className="font-medium">{activity.sap_detail.material_desc}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Plant:</span>{' '}
            <span className="font-medium">{activity.sap_detail.plant_code}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Quantity:</span>{' '}
            <span className="font-medium">
              {formatNumber(activity.sap_detail.quantity_normalized)} {activity.sap_detail.unit_normalized}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Classification:</span>{' '}
            <Badge size="sm">{activity.sap_detail.classification_method}</Badge>
          </div>
        </div>
      );
    }
    if (activity.utility_detail) {
      return (
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Service Number:</span>{' '}
            <span className="font-medium">{activity.utility_detail.service_number}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Tariff:</span>{' '}
            <span className="font-medium">{activity.utility_detail.tariff_category}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Consumption:</span>{' '}
            <span className="font-medium">
              {formatNumber(activity.utility_detail.kwh_consumed)} kWh
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Amount:</span>{' '}
            <span className="font-medium">{formatCurrency(activity.utility_detail.billing_amount_inr)}</span>
          </div>
        </div>
      );
    }
    if (activity.travel_detail) {
      return (
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Mode:</span>{' '}
            <span className="font-medium">{activity.travel_detail.mode}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Employee:</span>{' '}
            <span className="font-medium">{activity.travel_detail.employee_id}</span>
          </div>
          {activity.travel_detail.origin && (
            <div>
              <span className="text-muted-foreground">Route:</span>{' '}
              <span className="font-medium">
                {activity.travel_detail.origin} → {activity.travel_detail.destination}
              </span>
            </div>
          )}
          {activity.travel_detail.distance_km && (
            <div>
              <span className="text-muted-foreground">Distance:</span>{' '}
              <span className="font-medium">{formatNumber(activity.travel_detail.distance_km)} km</span>
            </div>
          )}
          <div>
            <span className="text-muted-foreground">Amount:</span>{' '}
            <span className="font-medium">
              {formatCurrency(activity.travel_detail.amount_raw, activity.travel_detail.currency)}
            </span>
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
        <Button
          variant="outline"
          onClick={() => setShowFilters(!showFilters)}
          className="gap-2"
        >
          <Filter className="h-4 w-4" />
          Filters
        </Button>
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
