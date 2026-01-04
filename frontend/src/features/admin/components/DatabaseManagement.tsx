// SPDX-FileCopyrightText: 2025 WeCode, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { useTranslation } from '@/hooks/useTranslation';
import { adminApis } from '@/apis/admin';
import { DownloadIcon, UploadIcon, AlertTriangleIcon, Loader2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

const DatabaseManagement: React.FC = () => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [showImportWarning, setShowImportWarning] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Handle database export
  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await adminApis.exportDatabase();

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `wegent_database_export_${new Date().toISOString().split('T')[0]}.sql`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast({
        title: t('admin:database.export.success'),
        description: t('admin:database.export.success_description'),
      });
    } catch (error) {
      console.error('Export failed:', error);
      toast({
        variant: 'destructive',
        title: t('admin:database.export.failed'),
        description:
          error instanceof Error ? error.message : t('admin:database.export.failed_description'),
      });
    } finally {
      setExporting(false);
    }
  };

  // Handle file selection
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.sql')) {
      toast({
        variant: 'destructive',
        title: t('admin:database.import.invalid_file'),
        description: t('admin:database.import.invalid_file_description'),
      });
      return;
    }

    // Validate file size (500MB max)
    const maxSize = 500 * 1024 * 1024; // 500 MB
    if (file.size > maxSize) {
      toast({
        variant: 'destructive',
        title: t('admin:database.import.file_too_large'),
        description: t('admin:database.import.file_too_large_description'),
      });
      return;
    }

    setSelectedFile(file);
    setShowImportWarning(true);
  };

  // Handle database import
  const handleImport = async () => {
    if (!selectedFile) return;

    setImporting(true);
    setShowImportWarning(false);

    try {
      const result = await adminApis.importDatabase(selectedFile);

      toast({
        title: t('admin:database.import.success'),
        description: t('admin:database.import.success_description', {
          filename: selectedFile.name,
          size: result.file_size_mb.toFixed(2),
        }),
      });

      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      setSelectedFile(null);
    } catch (error) {
      console.error('Import failed:', error);
      toast({
        variant: 'destructive',
        title: t('admin:database.import.failed'),
        description:
          error instanceof Error ? error.message : t('admin:database.import.failed_description'),
      });
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-text-primary">{t('admin:database.title')}</h2>
        <p className="text-text-secondary mt-1">{t('admin:database.description')}</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Export Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DownloadIcon className="w-5 h-5" />
              {t('admin:database.export.title')}
            </CardTitle>
            <CardDescription>{t('admin:database.export.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={handleExport}
              disabled={exporting}
              className="w-full"
              variant="default"
            >
              {exporting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {t('admin:database.export.exporting')}
                </>
              ) : (
                <>
                  <DownloadIcon className="w-4 h-4 mr-2" />
                  {t('admin:database.export.button')}
                </>
              )}
            </Button>
            <p className="text-sm text-text-secondary mt-4">{t('admin:database.export.note')}</p>
          </CardContent>
        </Card>

        {/* Import Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UploadIcon className="w-5 h-5" />
              {t('admin:database.import.title')}
            </CardTitle>
            <CardDescription>{t('admin:database.import.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <input
              ref={fileInputRef}
              type="file"
              accept=".sql"
              onChange={handleFileSelect}
              className="hidden"
              id="database-import-file"
            />
            <Button
              onClick={() => fileInputRef.current?.click()}
              disabled={importing}
              className="w-full"
              variant="outline"
            >
              {importing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {t('admin:database.import.importing')}
                </>
              ) : (
                <>
                  <UploadIcon className="w-4 h-4 mr-2" />
                  {t('admin:database.import.button')}
                </>
              )}
            </Button>
            {selectedFile && (
              <p className="text-sm text-text-secondary mt-2">
                {t('admin:database.import.selected_file')}: {selectedFile.name} (
                {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
              </p>
            )}
            <p className="text-sm text-text-secondary mt-4">{t('admin:database.import.note')}</p>
          </CardContent>
        </Card>
      </div>

      {/* Warning Dialog */}
      <AlertDialog open={showImportWarning} onOpenChange={setShowImportWarning}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangleIcon className="w-5 h-5 text-destructive" />
              {t('admin:database.import.warning_title')}
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-2">
              <p>{t('admin:database.import.warning_message')}</p>
              <p className="font-semibold text-destructive">
                {t('admin:database.import.warning_emphasis')}
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('admin:common.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleImport}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('admin:database.import.confirm_import')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default DatabaseManagement;
