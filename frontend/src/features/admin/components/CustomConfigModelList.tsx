// SPDX-FileCopyrightText: 2025 WeCode, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CpuChipIcon, TrashIcon, CircleStackIcon } from '@heroicons/react/24/outline';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Tag } from '@/components/ui/tag';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
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
import { useToast } from '@/hooks/use-toast';
import { useTranslation } from '@/hooks/useTranslation';
import {
  adminApis,
  AdminCustomConfigModel,
  AdminCustomConfigModelCleanupResponse,
  ApiKeyStatus,
} from '@/apis/admin';

const CustomConfigModelList: React.FC = () => {
  const { t } = useTranslation();
  const { toast } = useToast();

  const [models, setModels] = useState<AdminCustomConfigModel[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [search, setSearch] = useState('');

  const [selectedModel, setSelectedModel] = useState<AdminCustomConfigModel | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [forceDelete, setForceDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [isCleanupDialogOpen, setIsCleanupDialogOpen] = useState(false);
  const [cleanupPreview, setCleanupPreview] =
    useState<AdminCustomConfigModelCleanupResponse | null>(null);
  const [cleanupPreviewLoading, setCleanupPreviewLoading] = useState(false);
  const [cleaning, setCleaning] = useState(false);

  const fetchModels = useCallback(async () => {
    setLoading(true);
    try {
      const response = await adminApis.getCustomConfigModels(1, 500, includeInactive, search, 5);
      setModels(response.items);
      setTotal(response.total);
    } catch (error) {
      toast({
        variant: 'destructive',
        title: t('admin:custom_config_models.errors.load_failed'),
        description: (error as Error).message,
      });
    } finally {
      setLoading(false);
    }
  }, [includeInactive, search, toast, t]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchModels();
    }, 300);
    return () => clearTimeout(timer);
  }, [fetchModels]);

  const getApiKeyTagVariant = (
    status: ApiKeyStatus
  ): 'default' | 'success' | 'info' | 'warning' | 'error' => {
    if (status === 'SET') return 'success';
    if (status === 'PLACEHOLDER') return 'warning';
    if (status === 'EMPTY') return 'error';
    return 'default';
  };

  const getReferencesTagVariant = (
    count: number
  ): 'default' | 'success' | 'info' | 'warning' | 'error' => {
    if (count > 0) return 'warning';
    return 'success';
  };

  const openDeleteDialog = (model: AdminCustomConfigModel) => {
    setSelectedModel(model);
    setForceDelete(false);
    setIsDeleteDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!selectedModel) return;
    setDeleting(true);
    try {
      await adminApis.deleteCustomConfigModel(selectedModel.id, forceDelete);
      toast({ title: t('admin:custom_config_models.success.deleted') });
      setIsDeleteDialogOpen(false);
      setSelectedModel(null);
      fetchModels();
    } catch (error) {
      toast({
        variant: 'destructive',
        title: t('admin:custom_config_models.errors.delete_failed'),
        description: (error as Error).message,
      });
    } finally {
      setDeleting(false);
    }
  };

  const handleOpenCleanupDialog = useCallback(async () => {
    setIsCleanupDialogOpen(true);
    setCleanupPreview(null);
    setCleanupPreviewLoading(true);
    try {
      const preview = await adminApis.cleanupCustomConfigModelOrphans(true, 0);
      setCleanupPreview(preview);
    } catch (error) {
      toast({
        variant: 'destructive',
        title: t('admin:custom_config_models.errors.cleanup_preview_failed'),
        description: (error as Error).message,
      });
    } finally {
      setCleanupPreviewLoading(false);
    }
  }, [toast, t]);

  const handleCleanupOrphans = async () => {
    setCleaning(true);
    try {
      const result = await adminApis.cleanupCustomConfigModelOrphans(false, 0);
      toast({
        title: t('admin:custom_config_models.success.cleaned'),
        description: t('admin:custom_config_models.cleaned_result', { count: result.deleted }),
      });
      setIsCleanupDialogOpen(false);
      fetchModels();
    } catch (error) {
      toast({
        variant: 'destructive',
        title: t('admin:custom_config_models.errors.cleanup_failed'),
        description: (error as Error).message,
      });
    } finally {
      setCleaning(false);
    }
  };

  const headerRight = useMemo(() => {
    return (
      <div className="flex flex-col gap-2 md:flex-row md:items-center">
        <div className="flex items-center gap-2">
          <Input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder={t('admin:custom_config_models.search_placeholder')}
            className="w-full md:w-72"
          />
          <Button variant="outline" onClick={() => fetchModels()} disabled={loading}>
            {t('admin:custom_config_models.search')}
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <Switch
            id="admin-custom-config-models-include-inactive"
            checked={includeInactive}
            onCheckedChange={setIncludeInactive}
          />
          <Label htmlFor="admin-custom-config-models-include-inactive" className="text-sm">
            {t('admin:custom_config_models.show_inactive')}
          </Label>
        </div>

        <Button variant="outline" onClick={handleOpenCleanupDialog} disabled={loading || cleaning}>
          {t('admin:custom_config_models.cleanup_orphans')}
        </Button>
      </div>
    );
  }, [cleaning, fetchModels, handleOpenCleanupDialog, includeInactive, loading, search, t]);

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-text-primary mb-1">
            {t('admin:custom_config_models.title')}
          </h2>
          <p className="text-sm text-text-muted">{t('admin:custom_config_models.description')}</p>
          <p className="text-xs text-text-muted mt-1">
            {t('admin:custom_config_models.total_label', { total })}
          </p>
        </div>
        {headerRight}
      </div>

      <div className="bg-base border border-border rounded-md p-2 w-full max-h-[70vh] flex flex-col overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-text-muted" />
          </div>
        )}

        {!loading && models.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <CircleStackIcon className="w-12 h-12 text-text-muted mb-4" />
            <p className="text-text-muted">{t('admin:custom_config_models.no_models')}</p>
          </div>
        )}

        {!loading && models.length > 0 && (
          <div className="flex-1 overflow-y-auto space-y-3 p-1">
            {models.map(model => (
              <Card
                key={model.id}
                className="p-4 bg-base hover:bg-hover transition-colors border-l-2 border-l-warning"
              >
                <div className="flex items-center justify-between min-w-0">
                  <div className="flex items-center space-x-3 min-w-0 flex-1">
                    <CpuChipIcon className="w-5 h-5 text-warning flex-shrink-0" />
                    <div className="flex flex-col justify-center min-w-0 flex-1">
                      <div className="flex items-center gap-2 min-w-0 flex-wrap">
                        <h3 className="text-base font-medium text-text-primary truncate max-w-[480px]">
                          {model.name}
                        </h3>
                        <Tag variant="info">
                          {model.user_name ||
                            `${t('admin:custom_config_models.user_id')}:${model.user_id}`}
                        </Tag>
                        <Tag variant="info">{model.provider || 'unknown'}</Tag>
                        <Tag variant={getApiKeyTagVariant(model.api_key_status)}>
                          {t(
                            `admin:custom_config_models.api_key_status.${model.api_key_status.toLowerCase()}`
                          )}
                        </Tag>
                        <Tag variant={getReferencesTagVariant(model.referenced_by_bots)}>
                          {t('admin:custom_config_models.referenced_by_bots', {
                            count: model.referenced_by_bots,
                          })}
                        </Tag>
                        {model.is_active ? (
                          <Tag variant="success">
                            {t('admin:custom_config_models.status.active')}
                          </Tag>
                        ) : (
                          <Tag variant="error">
                            {t('admin:custom_config_models.status.inactive')}
                          </Tag>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-xs text-text-muted flex-wrap">
                        <span>
                          {t('admin:custom_config_models.namespace_label')}: {model.namespace}
                        </span>
                        <span>•</span>
                        <span>
                          {t('admin:custom_config_models.model_id')}: {model.model_id || 'N/A'}
                        </span>
                        <span>•</span>
                        <span className="truncate max-w-[520px]">
                          {t('admin:custom_config_models.base_url')}: {model.base_url || 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 flex-shrink-0 ml-3">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 hover:text-error"
                      onClick={() => openDeleteDialog(model)}
                      title={t('admin:custom_config_models.delete_model')}
                    >
                      <TrashIcon className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t('admin:custom_config_models.confirm.delete_title')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('admin:custom_config_models.confirm.delete_message', {
                name: selectedModel?.name || '',
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>

          {selectedModel && selectedModel.referenced_by_bots > 0 && (
            <div className="space-y-2 mt-2">
              <div className="text-sm text-warning">
                {t('admin:custom_config_models.confirm.referenced_warning', {
                  count: selectedModel.referenced_by_bots,
                })}
              </div>
              {selectedModel.referenced_bots.length > 0 && (
                <div className="text-xs text-text-muted">
                  {selectedModel.referenced_bots.map(b => (
                    <div key={b.id}>{`${b.namespace}/${b.name}`}</div>
                  ))}
                </div>
              )}
              <div className="flex items-center gap-2">
                <Switch
                  id="admin-custom-config-models-force-delete"
                  checked={forceDelete}
                  onCheckedChange={setForceDelete}
                />
                <Label htmlFor="admin-custom-config-models-force-delete" className="text-sm">
                  {t('admin:custom_config_models.force_delete')}
                </Label>
              </div>
            </div>
          )}

          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>{t('admin:common.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={
                deleting ||
                (selectedModel?.referenced_by_bots
                  ? selectedModel.referenced_by_bots > 0 && !forceDelete
                  : false)
              }
              className="bg-error hover:bg-error/90"
            >
              {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : t('admin:common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={isCleanupDialogOpen} onOpenChange={setIsCleanupDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t('admin:custom_config_models.confirm.cleanup_title')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {cleanupPreviewLoading && t('admin:custom_config_models.confirm.cleanup_loading')}
              {!cleanupPreviewLoading &&
                cleanupPreview &&
                t('admin:custom_config_models.confirm.cleanup_message', {
                  count: cleanupPreview.candidates,
                })}
              {!cleanupPreviewLoading &&
                !cleanupPreview &&
                t('admin:custom_config_models.confirm.cleanup_message', { count: 0 })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={cleaning}>{t('admin:common.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleCleanupOrphans}
              disabled={
                cleaning ||
                cleanupPreviewLoading ||
                (cleanupPreview ? cleanupPreview.candidates === 0 : false)
              }
              className="bg-warning hover:bg-warning/90"
            >
              {cleaning ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                t('admin:custom_config_models.cleanup_orphans')
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default CustomConfigModelList;
