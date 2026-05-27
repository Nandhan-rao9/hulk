import { useState, useEffect } from 'react';
import { FileText, CheckCircle, XCircle, Clock } from 'lucide-react';
import { Card } from '../components/Card';
import Badge from '../components/Badge';
import { sourceFilesApi, type SourceFile } from '../lib/api';
import { formatDate } from '../lib/utils';

export default function Files() {
  const [files, setFiles] = useState<SourceFile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const response = await sourceFilesApi.list();
      setFiles(response.data.results);
    } catch (error) {
      console.error('Failed to fetch files:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'DONE':
        return <CheckCircle className="h-5 w-5 text-brand-600" />;
      case 'FAILED':
        return <XCircle className="h-5 w-5 text-destructive" />;
      case 'PROCESSING':
        return <Clock className="h-5 w-5 text-yellow-600 animate-pulse" />;
      default:
        return <FileText className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      DONE: { variant: 'success', label: 'Done' },
      FAILED: { variant: 'danger', label: 'Failed' },
      PROCESSING: { variant: 'warning', label: 'Processing' },
    };
    const config = variants[status] || { variant: 'default', label: status };
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold tracking-tight mb-2">Uploaded Files</h1>
        <p className="text-muted-foreground text-lg">
          {files.length} files • View ingestion history and statistics
        </p>
      </div>

      <div className="grid gap-4">
        {loading ? (
          <Card>
            <div className="p-12 text-center text-muted-foreground">
              Loading files...
            </div>
          </Card>
        ) : files.length === 0 ? (
          <Card>
            <div className="p-12 text-center text-muted-foreground">
              No files uploaded yet
            </div>
          </Card>
        ) : (
          files.map((file) => (
            <Card key={file.id} hover>
              <div className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    <div className="h-12 w-12 rounded-lg bg-muted flex items-center justify-center flex-shrink-0">
                      {getStatusIcon(file.status)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-lg font-semibold truncate">
                          {file.original_filename.split('/').pop()}
                        </h3>
                        {getStatusBadge(file.status)}
                        <Badge variant="default" size="sm">{file.source_type}</Badge>
                      </div>
                      <div className="flex items-center space-x-6 text-sm text-muted-foreground">
                        <div>
                          Uploaded by <span className="font-medium">{file.uploaded_by_name}</span>
                        </div>
                        <div>{formatDate(file.uploaded_at)}</div>
                      </div>
                    </div>
                  </div>
                  {file.status === 'DONE' && (
                    <div className="flex items-center space-x-6 ml-6">
                      <div className="text-center">
                        <div className="text-2xl font-semibold">{file.total_rows}</div>
                        <div className="text-xs text-muted-foreground">Total</div>
                      </div>
                      {file.failed_rows! > 0 && (
                        <div className="text-center">
                          <div className="text-2xl font-semibold text-destructive">{file.failed_rows}</div>
                          <div className="text-xs text-muted-foreground">Failed</div>
                        </div>
                      )}
                      {file.flagged_rows! > 0 && (
                        <div className="text-center">
                          <div className="text-2xl font-semibold text-yellow-600">{file.flagged_rows}</div>
                          <div className="text-xs text-muted-foreground">Flagged</div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
