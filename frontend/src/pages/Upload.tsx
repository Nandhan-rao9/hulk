import { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Upload as UploadIcon, FileUp, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import Button from '../components/Button';
import Badge from '../components/Badge';
import { sourceFilesApi, type SourceFile } from '../lib/api';

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [sourceType, setSourceType] = useState<string>('SAP');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<SourceFile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.csv')) {
        setFile(droppedFile);
        setError(null);
        setResult(null);
      } else {
        setError('Please upload a CSV file');
      }
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const response = await sourceFilesApi.upload(file, sourceType);
      setResult(response.data);
      setFile(null);
    } catch (err: any) {
      const d = err.response?.data;
      const errorMessage =
        d?.detail ||
        d?.non_field_errors?.[0] ||
        d?.file?.[0] ||
        (typeof d === 'string' ? d : null) ||
        err.message ||
        'Upload failed';
      setError(errorMessage);
      console.error('Upload error:', d); // Log full error for debugging
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-4xl font-bold tracking-tight mb-2">Upload Data</h1>
        <p className="text-muted-foreground text-lg">
          Upload SAP, Utility, or Travel expense CSV files for emissions tracking
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>File Upload</CardTitle>
          <CardDescription>Select source type and upload your CSV file</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Source Type Selector */}
          <div>
            <label className="block text-sm font-medium mb-3">Source Type</label>
            <div className="grid grid-cols-4 gap-3">
              {[
                { value: 'SAP', label: 'SAP MB51', desc: 'Material documents' },
                { value: 'UTILITY', label: 'Utility Bills', desc: 'Electricity' },
                { value: 'TRAVEL_CONCUR', label: 'Concur', desc: 'Travel expenses' },
                { value: 'TRAVEL_NAVAN', label: 'Navan', desc: 'Travel expenses' },
              ].map((type) => (
                <button
                  key={type.value}
                  onClick={() => setSourceType(type.value)}
                  className={`p-4 rounded-lg border-2 text-left transition-all ${
                    sourceType === type.value
                      ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
                      : 'border-border hover:border-brand-300'
                  }`}
                >
                  <div className="font-medium text-sm">{type.label}</div>
                  <div className="text-xs text-muted-foreground mt-1">{type.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* File Drop Zone */}
          <div>
            <label className="block text-sm font-medium mb-3">CSV File</label>
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`relative border-2 border-dashed rounded-lg p-12 text-center transition-all ${
                dragActive
                  ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
                  : 'border-border hover:border-brand-300'
              }`}
            >
              <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <div className="flex flex-col items-center space-y-4">
                <div className="h-16 w-16 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                  {file ? (
                    <FileUp className="h-8 w-8 text-brand-600" />
                  ) : (
                    <UploadIcon className="h-8 w-8 text-brand-600" />
                  )}
                </div>
                {file ? (
                  <div>
                    <p className="text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {(file.size / 1024).toFixed(2)} KB
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-medium">
                      Drop your CSV file here, or click to browse
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Maximum file size: 50 MB
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Upload Button */}
          <Button
            onClick={handleUpload}
            disabled={!file || uploading}
            isLoading={uploading}
            size="lg"
            className="w-full"
          >
            {uploading ? 'Uploading...' : 'Upload and Ingest'}
          </Button>
        </CardContent>
      </Card>

      {/* Result Card */}
      {result && (
        <Card className="border-brand-200 dark:border-brand-900 animate-slide-in">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3">
                <div className="h-10 w-10 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                  <CheckCircle className="h-6 w-6 text-brand-600" />
                </div>
                <div>
                  <CardTitle className="text-xl">Upload Successful</CardTitle>
                  <CardDescription>{result.original_filename}</CardDescription>
                </div>
              </div>
              <Badge variant="success">{result.status}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-4 gap-6 p-4 bg-muted/50 rounded-lg">
              <div>
                <div className="text-sm text-muted-foreground mb-1">Total Rows</div>
                <div className="text-2xl font-semibold">{result.total_rows}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground mb-1">Auto-Approved</div>
                <div className="text-2xl font-semibold text-brand-600">{result.approved_rows}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground mb-1">Failed Rows</div>
                <div className="text-2xl font-semibold text-destructive">{result.failed_rows}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground mb-1">Flagged Rows</div>
                <div className="text-2xl font-semibold text-yellow-600">{result.flagged_rows}</div>
              </div>
            </div>

            {/* Next Steps Guide */}
            <div className="p-4 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900 rounded-lg">
              <div className="flex items-start space-x-3">
                <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="font-medium text-blue-900 dark:text-blue-100 mb-2">
                    📋 Next Steps
                  </div>
                  <div className="text-sm text-blue-800 dark:text-blue-200 space-y-2">
                    <p>
                      <strong>{result.approved_rows || 0} activities</strong> were automatically approved (no flags detected).
                    </p>
                    {result.flagged_rows! > 0 && (
                      <p>
                        <strong>{result.flagged_rows} flagged activities</strong> require review.
                      </p>
                    )}
                    {result.flagged_rows! > 0 && (
                      <p className="font-medium">
                        → Go to <Link to="/review" className="text-brand-600 underline hover:text-brand-700">Review Queue</Link> to review flagged activities
                      </p>
                    )}
                    {result.flagged_rows === 0 && (
                      <p className="font-medium">
                        → View activities in <Link to={`/files/${result.id}`} className="text-brand-600 underline hover:text-brand-700">File Details</Link>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error Card */}
      {error && (
        <Card className="border-destructive animate-slide-in">
          <CardContent className="pt-6">
            <div className="flex items-start space-x-3">
              <XCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-medium text-destructive mb-1">Upload Failed</div>
                <div className="text-sm text-muted-foreground">{error}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Info Card */}
      <Card className="bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-900">
        <CardContent className="pt-6">
          <div className="flex items-start space-x-3">
            <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="space-y-2 text-sm">
              <div className="font-medium text-blue-900 dark:text-blue-100">CSV Format Requirements</div>
              <ul className="space-y-1 text-blue-800 dark:text-blue-200">
                <li><span className="font-medium">SAP:</span> Must have WERKS, MATNR, MENGE, MEINS, BUDAT columns</li>
                <li><span className="font-medium">Utility:</span> Must have service_no, period_start, period_end, units_kwh columns</li>
                <li><span className="font-medium">Travel:</span> Must have trip_id, employee_id, travel_date, mode, amount columns</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
