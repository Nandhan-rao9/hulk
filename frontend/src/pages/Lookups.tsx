import { useState } from 'react';
import { Upload as UploadIcon, FileUp, CheckCircle, XCircle, AlertTriangle, Table, MapPin } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import Button from '../components/Button';
import { lookupsApi, type LookupUploadResponse } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

type LookupType = 'plant' | 'material';

export default function Lookups() {
  const { isAdmin } = useAuth();
  const [plantFile, setPlantFile] = useState<File | null>(null);
  const [materialFile, setMaterialFile] = useState<File | null>(null);
  const [plantUploading, setPlantUploading] = useState(false);
  const [materialUploading, setMaterialUploading] = useState(false);
  const [plantResult, setPlantResult] = useState<LookupUploadResponse | null>(null);
  const [materialResult, setMaterialResult] = useState<LookupUploadResponse | null>(null);

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-6xl mb-4">🔒</div>
              <h2 className="text-2xl font-bold mb-2">Admin Access Required</h2>
              <p className="text-muted-foreground">
                Lookup table management is only available to administrators.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const handleFileChange = (type: LookupType, file: File | null) => {
    if (type === 'plant') {
      setPlantFile(file);
      setPlantResult(null);
    } else {
      setMaterialFile(file);
      setMaterialResult(null);
    }
  };

  const handleUpload = async (type: LookupType) => {
    const file = type === 'plant' ? plantFile : materialFile;
    if (!file) return;

    const setUploading = type === 'plant' ? setPlantUploading : setMaterialUploading;
    const setResult = type === 'plant' ? setPlantResult : setMaterialResult;
    const setFile = type === 'plant' ? setPlantFile : setMaterialFile;

    setUploading(true);

    try {
      const uploadFn = type === 'plant'
        ? lookupsApi.uploadPlantLookup
        : lookupsApi.uploadMaterialMapping;

      const response = await uploadFn(file);
      setResult(response.data);
      if (response.data.status === 'success') {
        setFile(null);
      }
    } catch (err: any) {
      const d = err.response?.data;
      const errorMessage = d?.detail || 'Upload failed';
      setResult({
        status: 'error',
        total_rows: 0,
        created: 0,
        updated: 0,
        skipped: 0,
        errors: [{ row: 0, field: 'file', error: errorMessage }]
      });
    } finally {
      setUploading(false);
    }
  };

  const renderResult = (result: LookupUploadResponse | null) => {
    if (!result) return null;

    const isSuccess = result.status === 'success' && result.errors.length === 0;

    return (
      <Card className={`animate-slide-in ${isSuccess ? 'border-brand-200 dark:border-brand-900' : 'border-destructive'}`}>
        <CardHeader>
          <div className="flex items-center space-x-3">
            <div className={`h-10 w-10 rounded-full flex items-center justify-center ${
              isSuccess ? 'bg-brand-100 dark:bg-brand-900/30' : 'bg-red-100 dark:bg-red-900/30'
            }`}>
              {isSuccess ? (
                <CheckCircle className="h-6 w-6 text-brand-600" />
              ) : (
                <XCircle className="h-6 w-6 text-destructive" />
              )}
            </div>
            <div>
              <CardTitle className="text-xl">
                {isSuccess ? 'Upload Successful' : 'Upload Failed'}
              </CardTitle>
              <CardDescription>
                {result.total_rows} rows processed
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4 p-4 bg-muted/50 rounded-lg mb-4">
            <div>
              <div className="text-sm text-muted-foreground mb-1">Created</div>
              <div className="text-2xl font-semibold text-brand-600">{result.created}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground mb-1">Updated</div>
              <div className="text-2xl font-semibold text-blue-600">{result.updated}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground mb-1">Skipped</div>
              <div className="text-2xl font-semibold text-yellow-600">{result.skipped}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground mb-1">Errors</div>
              <div className="text-2xl font-semibold text-destructive">{result.errors.length}</div>
            </div>
          </div>

          {result.errors.length > 0 && (
            <div className="space-y-2">
              <div className="font-medium text-destructive flex items-center space-x-2">
                <AlertTriangle className="h-4 w-4" />
                <span>Validation Errors:</span>
              </div>
              <div className="max-h-60 overflow-y-auto space-y-1">
                {result.errors.map((error, idx) => (
                  <div key={idx} className="text-sm p-2 bg-destructive/10 rounded border border-destructive/20">
                    <span className="font-medium">Row {error.row}</span> -
                    <span className="text-muted-foreground"> {error.field}: </span>
                    <span>{error.error}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-4xl font-bold tracking-tight mb-2">Lookup Tables</h1>
        <p className="text-muted-foreground text-lg">
          Manage plant mappings and material group classifications
        </p>
      </div>

      {/* Plant Lookup Upload */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
              <MapPin className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <CardTitle>Plant Lookup Table</CardTitle>
              <CardDescription>
                Map SAP plant codes and utility meter IDs to facilities
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900 rounded-lg">
            <div className="text-sm text-blue-900 dark:text-blue-100 font-medium mb-2">
              CSV Format:
            </div>
            <pre className="text-xs text-blue-800 dark:text-blue-200 font-mono">
source_type,code,facility_name,city,country{'\n'}
SAP,1000,Mumbai Plant,Mumbai,India{'\n'}
UTILITY,12345678,Mumbai Plant,Mumbai,India
            </pre>
          </div>

          <div className="border-2 border-dashed rounded-lg p-8 text-center">
            <input
              type="file"
              accept=".csv"
              onChange={(e) => handleFileChange('plant', e.target.files?.[0] || null)}
              className="hidden"
              id="plant-file-input"
            />
            <label htmlFor="plant-file-input" className="cursor-pointer">
              <div className="flex flex-col items-center space-y-3">
                <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center">
                  {plantFile ? (
                    <FileUp className="h-6 w-6 text-brand-600" />
                  ) : (
                    <UploadIcon className="h-6 w-6 text-muted-foreground" />
                  )}
                </div>
                {plantFile ? (
                  <div>
                    <p className="text-sm font-medium">{plantFile.name}</p>
                    <p className="text-xs text-muted-foreground">{(plantFile.size / 1024).toFixed(2)} KB</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-medium">Click to select CSV file</p>
                    <p className="text-xs text-muted-foreground">Maximum 10 MB</p>
                  </div>
                )}
              </div>
            </label>
          </div>

          <Button
            onClick={() => handleUpload('plant')}
            disabled={!plantFile || plantUploading}
            isLoading={plantUploading}
            className="w-full"
          >
            {plantUploading ? 'Uploading...' : 'Upload Plant Lookup'}
          </Button>
        </CardContent>
      </Card>

      {renderResult(plantResult)}

      {/* Material Mapping Upload */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
              <Table className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <CardTitle>Material Group Mapping</CardTitle>
              <CardDescription>
                Map SAP material group codes (MATKL) to fuel types and scopes
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 bg-purple-50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-900 rounded-lg">
            <div className="text-sm text-purple-900 dark:text-purple-100 font-medium mb-2">
              CSV Format:
            </div>
            <pre className="text-xs text-purple-800 dark:text-purple-200 font-mono">
matkl_code,fuel_type,scope{'\n'}
DIESEL01,DIESEL,1{'\n'}
PETROL02,PETROL,1
            </pre>
            <div className="text-xs text-purple-800 dark:text-purple-200 mt-2">
              Valid fuel types: DIESEL, PETROL, NATGAS, LPG, FUEL_OIL, COAL, KEROSENE, ELECTRICITY
            </div>
          </div>

          <div className="border-2 border-dashed rounded-lg p-8 text-center">
            <input
              type="file"
              accept=".csv"
              onChange={(e) => handleFileChange('material', e.target.files?.[0] || null)}
              className="hidden"
              id="material-file-input"
            />
            <label htmlFor="material-file-input" className="cursor-pointer">
              <div className="flex flex-col items-center space-y-3">
                <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center">
                  {materialFile ? (
                    <FileUp className="h-6 w-6 text-brand-600" />
                  ) : (
                    <UploadIcon className="h-6 w-6 text-muted-foreground" />
                  )}
                </div>
                {materialFile ? (
                  <div>
                    <p className="text-sm font-medium">{materialFile.name}</p>
                    <p className="text-xs text-muted-foreground">{(materialFile.size / 1024).toFixed(2)} KB</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-medium">Click to select CSV file</p>
                    <p className="text-xs text-muted-foreground">Maximum 10 MB</p>
                  </div>
                )}
              </div>
            </label>
          </div>

          <Button
            onClick={() => handleUpload('material')}
            disabled={!materialFile || materialUploading}
            isLoading={materialUploading}
            className="w-full"
          >
            {materialUploading ? 'Uploading...' : 'Upload Material Mapping'}
          </Button>

          <div className="p-3 bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-900 rounded-lg">
            <div className="flex items-start space-x-2">
              <AlertTriangle className="h-4 w-4 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-yellow-900 dark:text-yellow-100">
                <span className="font-medium">Note:</span> Material mappings cannot be updated once created.
                If a MATKL code already exists, the upload will return an error for that row.
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {renderResult(materialResult)}
    </div>
  );
}
