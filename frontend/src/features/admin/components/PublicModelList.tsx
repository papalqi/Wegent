// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Tag } from '@/components/ui/tag'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import {
  CpuChipIcon,
  PencilIcon,
  TrashIcon,
  GlobeAltIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@heroicons/react/24/outline'
import { Loader2 } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { useTranslation } from '@/hooks/useTranslation'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  adminApis,
  AdminPublicModel,
  AdminPublicModelCreate,
  AdminPublicModelUpdate,
} from '@/apis/admin'
import UnifiedAddButton from '@/components/common/UnifiedAddButton'
import { getProviderBaseUrlResolvedForDisplay } from '@/features/settings/utils/provider-base-url'
import {
  buildPublicModelJson,
  extractApiKey,
  extractBaseUrl,
  extractCustomHeaders,
  extractDisplayName,
  extractModelId,
  extractProviderType,
  parseCustomHeaders,
  type PublicModelFormData,
  type ProviderType,
} from '@/features/admin/utils/public-model'

const INITIAL_FORM_DATA: PublicModelFormData = {
  name: '',
  displayName: '',
  providerType: 'openai',
  modelId: '',
  baseUrl: '',
  apiKey: '',
  customHeaders: '',
  useAdvancedJson: false,
  advancedJson: '',
  is_active: true,
}

const PublicModelList: React.FC = () => {
  const { t } = useTranslation(['admin', 'common'])
  const { toast } = useToast()
  const [models, setModels] = useState<AdminPublicModel[]>([])
  const [_total, setTotal] = useState(0)
  const [page, _setPage] = useState(1)
  const [loading, setLoading] = useState(true)

  // Dialog states
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [selectedModel, setSelectedModel] = useState<AdminPublicModel | null>(null)

  const KUBERNETES_NAME_REGEX = /^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$/

  // Form states
  const [formData, setFormData] = useState<PublicModelFormData>({ ...INITIAL_FORM_DATA })
  const [configError, setConfigError] = useState('')
  const [customHeadersError, setCustomHeadersError] = useState('')
  const [saving, setSaving] = useState(false)
  const [showApiKey, setShowApiKey] = useState(false)

  const fetchModels = useCallback(async () => {
    setLoading(true)
    try {
      // Use a larger limit to display all public models without pagination
      const response = await adminApis.getPublicModels(page, 100)
      setModels(response.items)
      setTotal(response.total)
    } catch (_error) {
      toast({
        variant: 'destructive',
        title: t('admin:public_models.errors.load_failed'),
      })
    } finally {
      setLoading(false)
    }
  }, [page, toast, t])

  useEffect(() => {
    fetchModels()
  }, [fetchModels])

  const validateJsonObject = (value: string): Record<string, unknown> | null => {
    if (!value.trim()) {
      setConfigError(t('admin:public_models.errors.config_required'))
      return null
    }
    try {
      const parsed = JSON.parse(value)
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        setConfigError(t('admin:public_models.errors.config_invalid_json'))
        return null
      }
      setConfigError('')
      return parsed as Record<string, unknown>
    } catch {
      setConfigError(t('admin:public_models.errors.config_invalid_json'))
      return null
    }
  }

  const validateCustomHeaders = (value: string): Record<string, string> | null => {
    if (!value.trim()) {
      setCustomHeadersError('')
      return {}
    }

    const parsed = parseCustomHeaders(value)
    if (!parsed) {
      setCustomHeadersError(t('common:models.errors.custom_headers_invalid_json'))
      return null
    }

    setCustomHeadersError('')
    return parsed
  }

  const baseUrlResolvedForDisplay = React.useMemo(() => {
    return getProviderBaseUrlResolvedForDisplay(formData.providerType, formData.baseUrl)
  }, [formData.baseUrl, formData.providerType])

  const apiKeyPlaceholder =
    formData.providerType === 'openai' || formData.providerType === 'openai-responses'
      ? 'sk-...'
      : formData.providerType === 'gemini'
        ? 'AIza...'
        : 'sk-ant-...'

  const handleCreateModel = async () => {
    if (!formData.name.trim()) {
      toast({
        variant: 'destructive',
        title: t('admin:public_models.errors.name_required'),
      })
      return
    }

    if (!KUBERNETES_NAME_REGEX.test(formData.name.trim())) {
      toast({
        variant: 'destructive',
        title: t('common:models.errors.name_invalid'),
      })
      return
    }

    let modelJson: Record<string, unknown> | null = null
    if (formData.useAdvancedJson) {
      modelJson = validateJsonObject(formData.advancedJson)
      if (!modelJson) {
        toast({
          variant: 'destructive',
          title: t('admin:public_models.errors.config_invalid_json'),
        })
        return
      }
    } else {
      if (!formData.modelId.trim()) {
        toast({
          variant: 'destructive',
          title: t('common:models.errors.model_id_required'),
        })
        return
      }

      if (!formData.apiKey.trim()) {
        toast({
          variant: 'destructive',
          title: t('common:models.errors.api_key_required'),
        })
        return
      }

      const headers = validateCustomHeaders(formData.customHeaders)
      if (headers === null) {
        toast({
          variant: 'destructive',
          title: t('common:models.errors.custom_headers_invalid'),
        })
        return
      }

      modelJson = buildPublicModelJson(null, {
        name: formData.name.trim(),
        displayName: formData.displayName,
        providerType: formData.providerType,
        modelId: formData.modelId,
        baseUrl: formData.baseUrl,
        apiKey: formData.apiKey,
        customHeaders: headers,
      })
    }

    setSaving(true)
    try {
      const createData: AdminPublicModelCreate = {
        name: formData.name.trim(),
        namespace: 'default',
        json: modelJson,
      }
      await adminApis.createPublicModel(createData)
      toast({ title: t('admin:public_models.success.created') })
      setIsCreateDialogOpen(false)
      resetForm()
      fetchModels()
    } catch (error) {
      toast({
        variant: 'destructive',
        title: t('admin:public_models.errors.create_failed'),
        description: (error as Error).message,
      })
    } finally {
      setSaving(false)
    }
  }

  const handleUpdateModel = async () => {
    if (!selectedModel) return

    if (!formData.name.trim()) {
      toast({
        variant: 'destructive',
        title: t('admin:public_models.errors.name_required'),
      })
      return
    }
    if (!KUBERNETES_NAME_REGEX.test(formData.name.trim())) {
      toast({
        variant: 'destructive',
        title: t('common:models.errors.name_invalid'),
      })
      return
    }

    let modelJson: Record<string, unknown> | null = null
    if (formData.useAdvancedJson) {
      modelJson = validateJsonObject(formData.advancedJson)
      if (!modelJson) {
        toast({
          variant: 'destructive',
          title: t('admin:public_models.errors.config_invalid_json'),
        })
        return
      }
    } else {
      if (!formData.modelId.trim()) {
        toast({
          variant: 'destructive',
          title: t('common:models.errors.model_id_required'),
        })
        return
      }

      if (!formData.apiKey.trim()) {
        toast({
          variant: 'destructive',
          title: t('common:models.errors.api_key_required'),
        })
        return
      }

      const headers = validateCustomHeaders(formData.customHeaders)
      if (headers === null) {
        toast({
          variant: 'destructive',
          title: t('common:models.errors.custom_headers_invalid'),
        })
        return
      }

      modelJson = buildPublicModelJson(selectedModel.json, {
        name: formData.name.trim(),
        displayName: formData.displayName,
        providerType: formData.providerType,
        modelId: formData.modelId,
        baseUrl: formData.baseUrl,
        apiKey: formData.apiKey,
        customHeaders: headers,
      })
    }

    setSaving(true)
    try {
      const updateData: AdminPublicModelUpdate = {}
      if (formData.name !== selectedModel.name) {
        updateData.name = formData.name
      }
      updateData.json = modelJson
      if (formData.is_active !== selectedModel.is_active) {
        updateData.is_active = formData.is_active
      }

      await adminApis.updatePublicModel(selectedModel.id, updateData)
      toast({ title: t('admin:public_models.success.updated') })
      setIsEditDialogOpen(false)
      resetForm()
      fetchModels()
    } catch (error) {
      toast({
        variant: 'destructive',
        title: t('admin:public_models.errors.update_failed'),
        description: (error as Error).message,
      })
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteModel = async () => {
    if (!selectedModel) return

    setSaving(true)
    try {
      await adminApis.deletePublicModel(selectedModel.id)
      toast({ title: t('admin:public_models.success.deleted') })
      setIsDeleteDialogOpen(false)
      setSelectedModel(null)
      fetchModels()
    } catch (error) {
      toast({
        variant: 'destructive',
        title: t('admin:public_models.errors.delete_failed'),
        description: (error as Error).message,
      })
    } finally {
      setSaving(false)
    }
  }

  const resetForm = () => {
    setFormData({ ...INITIAL_FORM_DATA })
    setConfigError('')
    setCustomHeadersError('')
    setShowApiKey(false)
    setSelectedModel(null)
  }

  const openCreateDialog = () => {
    resetForm()
    setIsCreateDialogOpen(true)
  }

  const openEditDialog = (model: AdminPublicModel) => {
    const providerType = extractProviderType(model.json)
    const customHeaders = extractCustomHeaders(model.json)

    setSelectedModel(model)
    setFormData({
      name: model.name,
      displayName: model.display_name || extractDisplayName(model.json) || '',
      providerType,
      modelId: extractModelId(model.json),
      baseUrl: extractBaseUrl(model.json),
      apiKey: extractApiKey(model.json),
      customHeaders:
        Object.keys(customHeaders).length > 0 ? JSON.stringify(customHeaders, null, 2) : '',
      useAdvancedJson: false,
      advancedJson: JSON.stringify(model.json, null, 2),
      is_active: model.is_active,
    })
    setConfigError('')
    setCustomHeadersError('')
    setShowApiKey(false)
    setIsEditDialogOpen(true)
  }

  const getModelProvider = (json: Record<string, unknown>): string => {
    const providerType = extractProviderType(json)
    if (providerType === 'anthropic') return 'Anthropic'
    if (providerType === 'gemini') return 'Gemini'
    if (providerType === 'openai-responses') return 'OpenAI Responses'
    return 'OpenAI'
  }

  const getModelId = (json: Record<string, unknown>): string => {
    return extractModelId(json) || 'N/A'
  }

  const getDisplayName = (model: AdminPublicModel): string => {
    // Use display_name from API response if available, otherwise fall back to name
    return model.display_name || model.name
  }

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-xl font-semibold text-text-primary mb-1">
          {t('admin:public_models.title')}
        </h2>
        <p className="text-sm text-text-muted">{t('admin:public_models.description')}</p>
      </div>

      <div className="bg-base border border-border rounded-md p-2 w-full max-h-[70vh] flex flex-col overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-text-muted" />
          </div>
        )}

        {!loading && models.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <CpuChipIcon className="w-12 h-12 text-text-muted mb-4" />
            <p className="text-text-muted">{t('admin:public_models.no_models')}</p>
          </div>
        )}

        {!loading && models.length > 0 && (
          <div className="flex-1 overflow-y-auto space-y-3 p-1">
            {models.map(model => (
              <Card
                key={model.id}
                className="p-4 bg-base hover:bg-hover transition-colors border-l-2 border-l-primary"
              >
                <div className="flex items-center justify-between min-w-0">
                  <div className="flex items-center space-x-3 min-w-0 flex-1">
                    <GlobeAltIcon className="w-5 h-5 text-primary flex-shrink-0" />
                    <div className="flex flex-col justify-center min-w-0 flex-1">
                      <div className="flex items-center space-x-2 min-w-0">
                        <h3 className="text-base font-medium text-text-primary truncate">
                          {getDisplayName(model)}
                        </h3>
                        <Tag variant="info">{getModelProvider(model.json)}</Tag>
                        {model.is_active ? (
                          <Tag variant="success">{t('admin:public_models.status.active')}</Tag>
                        ) : (
                          <Tag variant="error">{t('admin:public_models.status.inactive')}</Tag>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-xs text-text-muted">
                        <span>
                          {t('admin:public_models.form.name')}: {model.name}
                        </span>
                        <span>•</span>
                        <span>
                          {t('admin:public_models.model_id')}: {getModelId(model.json)}
                        </span>
                        <span>•</span>
                        <span>
                          {t('admin:public_models.namespace_label')}: {model.namespace}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0 ml-3">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => openEditDialog(model)}
                      title={t('admin:public_models.edit_model')}
                    >
                      <PencilIcon className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 hover:text-error"
                      onClick={() => {
                        setSelectedModel(model)
                        setIsDeleteDialogOpen(true)
                      }}
                      title={t('admin:public_models.delete_model')}
                    >
                      <TrashIcon className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {!loading && (
          <div className="border-t border-border pt-3 mt-3 bg-base">
            <div className="flex justify-center">
              <UnifiedAddButton onClick={openCreateDialog}>
                {t('admin:public_models.create_model')}
              </UnifiedAddButton>
            </div>
          </div>
        )}
      </div>

      <Dialog
        open={isCreateDialogOpen}
        onOpenChange={open => {
          setIsCreateDialogOpen(open)
          if (!open) resetForm()
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('admin:public_models.create_model')}</DialogTitle>
            <DialogDescription>{t('admin:public_models.description')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4 max-h-[70vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-sm font-medium">
                  {t('admin:public_models.form.name')} <span className="text-red-400">*</span>
                </Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder={t('admin:public_models.form.name_placeholder')}
                  className="bg-base"
                />
                <p className="text-xs text-text-muted">{t('common:models.id_hint')}</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="displayName" className="text-sm font-medium">
                  {t('common:models.display_name')}
                </Label>
                <Input
                  id="displayName"
                  value={formData.displayName}
                  onChange={e => setFormData(prev => ({ ...prev, displayName: e.target.value }))}
                  placeholder={t('common:models.display_name_placeholder')}
                  className="bg-base"
                />
                <p className="text-xs text-text-muted">{t('common:models.display_name_hint')}</p>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="providerType" className="text-sm font-medium">
                {t('common:models.provider_type')} <span className="text-red-400">*</span>
              </Label>
              <Select
                value={formData.providerType}
                onValueChange={value =>
                  setFormData(prev => ({
                    ...prev,
                    providerType: value as ProviderType,
                  }))
                }
              >
                <SelectTrigger className="bg-base">
                  <SelectValue placeholder={t('common:models.select_provider')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="openai">OpenAI</SelectItem>
                  <SelectItem value="openai-responses">OpenAI Responses</SelectItem>
                  <SelectItem value="anthropic">Anthropic</SelectItem>
                  <SelectItem value="gemini">Gemini</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-text-muted">{t('common:models.provider_hint')}</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="modelId" className="text-sm font-medium">
                {t('common:models.model_id')} <span className="text-red-400">*</span>
              </Label>
              <Input
                id="modelId"
                value={formData.modelId}
                onChange={e => setFormData(prev => ({ ...prev, modelId: e.target.value }))}
                placeholder="gpt-4o-mini"
                className="bg-base"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="baseUrl" className="text-sm font-medium">
                {t('common:models.base_url')}
              </Label>
              <Input
                id="baseUrl"
                value={formData.baseUrl}
                onChange={e => setFormData(prev => ({ ...prev, baseUrl: e.target.value }))}
                placeholder={
                  formData.providerType === 'openai' || formData.providerType === 'openai-responses'
                    ? 'https://api.openai.com'
                    : formData.providerType === 'gemini'
                      ? 'https://generativelanguage.googleapis.com'
                      : 'https://api.anthropic.com'
                }
                className="bg-base"
              />
              <p className="text-xs text-text-muted">{t('common:models.base_url_hint')}</p>
              {baseUrlResolvedForDisplay && (
                <p className="text-xs text-text-muted">
                  {t('common:models.base_url_resolved')}:&nbsp;
                  <span className="font-mono">{baseUrlResolvedForDisplay}</span>
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="apiKey" className="text-sm font-medium">
                {t('common:models.api_key')} <span className="text-red-400">*</span>
              </Label>
              <div className="relative">
                <Input
                  id="apiKey"
                  type={showApiKey ? 'text' : 'password'}
                  value={formData.apiKey}
                  onChange={e => setFormData(prev => ({ ...prev, apiKey: e.target.value }))}
                  placeholder={apiKeyPlaceholder}
                  className="bg-base pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-2 top-1/2 -translate-y-1/2 h-7 w-7"
                  onClick={() => setShowApiKey(!showApiKey)}
                >
                  {showApiKey ? (
                    <EyeSlashIcon className="w-4 h-4" />
                  ) : (
                    <EyeIcon className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="customHeaders" className="text-sm font-medium">
                {t('common:models.custom_headers')}
              </Label>
              <Textarea
                id="customHeaders"
                value={formData.customHeaders}
                onChange={e => {
                  setFormData(prev => ({ ...prev, customHeaders: e.target.value }))
                  validateCustomHeaders(e.target.value)
                }}
                placeholder='{"X-Foo":"bar"}'
                className={`font-mono text-sm min-h-[120px] bg-base ${
                  customHeadersError ? 'border-error' : ''
                }`}
              />
              <p className="text-xs text-text-muted">{t('common:models.custom_headers_hint')}</p>
              {customHeadersError && <p className="text-xs text-error">{customHeadersError}</p>}
            </div>

            <div className="flex items-center justify-between border-t border-border pt-3">
              <Label htmlFor="advancedJsonSwitch" className="text-sm font-medium">
                {t('admin:public_models.form.config')}
              </Label>
              <Switch
                id="advancedJsonSwitch"
                checked={formData.useAdvancedJson}
                onCheckedChange={checked => {
                  setFormData(prev => {
                    if (!checked) return { ...prev, useAdvancedJson: false }

                    const headers = parseCustomHeaders(prev.customHeaders) || {}
                    const json = buildPublicModelJson(null, {
                      name: prev.name.trim() || 'model',
                      displayName: prev.displayName,
                      providerType: prev.providerType,
                      modelId: prev.modelId || 'gpt-4o-mini',
                      baseUrl: prev.baseUrl,
                      apiKey: prev.apiKey || '${OPENAI_API_KEY}',
                      customHeaders: headers,
                    })
                    return {
                      ...prev,
                      useAdvancedJson: true,
                      advancedJson: JSON.stringify(json, null, 2),
                    }
                  })
                  setConfigError('')
                }}
              />
            </div>

            {formData.useAdvancedJson && (
              <div className="space-y-2">
                <Textarea
                  id="advancedJson"
                  value={formData.advancedJson}
                  onChange={e => {
                    setFormData(prev => ({ ...prev, advancedJson: e.target.value }))
                    validateJsonObject(e.target.value)
                  }}
                  placeholder={t('admin:public_models.form.config_placeholder')}
                  className={`font-mono text-sm min-h-[220px] bg-base ${
                    configError ? 'border-error' : ''
                  }`}
                />
                {configError && <p className="text-xs text-error">{configError}</p>}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              {t('admin:common.cancel')}
            </Button>
            <Button onClick={handleCreateModel} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('admin:common.create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={isEditDialogOpen}
        onOpenChange={open => {
          setIsEditDialogOpen(open)
          if (!open) resetForm()
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('admin:public_models.edit_model')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4 max-h-[70vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-name" className="text-sm font-medium">
                  {t('admin:public_models.form.name')} <span className="text-red-400">*</span>
                </Label>
                <Input
                  id="edit-name"
                  value={formData.name}
                  onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder={t('admin:public_models.form.name_placeholder')}
                  className="bg-base"
                />
                <p className="text-xs text-text-muted">{t('common:models.id_hint')}</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-displayName" className="text-sm font-medium">
                  {t('common:models.display_name')}
                </Label>
                <Input
                  id="edit-displayName"
                  value={formData.displayName}
                  onChange={e => setFormData(prev => ({ ...prev, displayName: e.target.value }))}
                  placeholder={t('common:models.display_name_placeholder')}
                  className="bg-base"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-providerType" className="text-sm font-medium">
                {t('common:models.provider_type')} <span className="text-red-400">*</span>
              </Label>
              <Select
                value={formData.providerType}
                onValueChange={value =>
                  setFormData(prev => ({
                    ...prev,
                    providerType: value as ProviderType,
                  }))
                }
              >
                <SelectTrigger className="bg-base">
                  <SelectValue placeholder={t('common:models.select_provider')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="openai">OpenAI</SelectItem>
                  <SelectItem value="openai-responses">OpenAI Responses</SelectItem>
                  <SelectItem value="anthropic">Anthropic</SelectItem>
                  <SelectItem value="gemini">Gemini</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-modelId" className="text-sm font-medium">
                {t('common:models.model_id')} <span className="text-red-400">*</span>
              </Label>
              <Input
                id="edit-modelId"
                value={formData.modelId}
                onChange={e => setFormData(prev => ({ ...prev, modelId: e.target.value }))}
                placeholder="gpt-4o-mini"
                className="bg-base"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-baseUrl" className="text-sm font-medium">
                {t('common:models.base_url')}
              </Label>
              <Input
                id="edit-baseUrl"
                value={formData.baseUrl}
                onChange={e => setFormData(prev => ({ ...prev, baseUrl: e.target.value }))}
                placeholder={
                  formData.providerType === 'openai' || formData.providerType === 'openai-responses'
                    ? 'https://api.openai.com'
                    : formData.providerType === 'gemini'
                      ? 'https://generativelanguage.googleapis.com'
                      : 'https://api.anthropic.com'
                }
                className="bg-base"
              />
              {baseUrlResolvedForDisplay && (
                <p className="text-xs text-text-muted">
                  {t('common:models.base_url_resolved')}:&nbsp;
                  <span className="font-mono">{baseUrlResolvedForDisplay}</span>
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-apiKey" className="text-sm font-medium">
                {t('common:models.api_key')} <span className="text-red-400">*</span>
              </Label>
              <div className="relative">
                <Input
                  id="edit-apiKey"
                  type={showApiKey ? 'text' : 'password'}
                  value={formData.apiKey}
                  onChange={e => setFormData(prev => ({ ...prev, apiKey: e.target.value }))}
                  placeholder={apiKeyPlaceholder}
                  className="bg-base pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-2 top-1/2 -translate-y-1/2 h-7 w-7"
                  onClick={() => setShowApiKey(!showApiKey)}
                >
                  {showApiKey ? (
                    <EyeSlashIcon className="w-4 h-4" />
                  ) : (
                    <EyeIcon className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-customHeaders" className="text-sm font-medium">
                {t('common:models.custom_headers')}
              </Label>
              <Textarea
                id="edit-customHeaders"
                value={formData.customHeaders}
                onChange={e => {
                  setFormData(prev => ({ ...prev, customHeaders: e.target.value }))
                  validateCustomHeaders(e.target.value)
                }}
                placeholder='{"X-Foo":"bar"}'
                className={`font-mono text-sm min-h-[120px] bg-base ${
                  customHeadersError ? 'border-error' : ''
                }`}
              />
              {customHeadersError && <p className="text-xs text-error">{customHeadersError}</p>}
            </div>

            <div className="flex items-center justify-between border-t border-border pt-3">
              <Label htmlFor="edit-advancedJsonSwitch" className="text-sm font-medium">
                {t('admin:public_models.form.config')}
              </Label>
              <Switch
                id="edit-advancedJsonSwitch"
                checked={formData.useAdvancedJson}
                onCheckedChange={checked => {
                  if (!selectedModel) return
                  setFormData(prev => {
                    if (!checked) return { ...prev, useAdvancedJson: false }

                    const headers = parseCustomHeaders(prev.customHeaders) || {}
                    const json = buildPublicModelJson(selectedModel.json, {
                      name: prev.name.trim() || selectedModel.name,
                      displayName: prev.displayName,
                      providerType: prev.providerType,
                      modelId: prev.modelId || extractModelId(selectedModel.json) || 'gpt-4o-mini',
                      baseUrl: prev.baseUrl,
                      apiKey:
                        prev.apiKey || extractApiKey(selectedModel.json) || '${OPENAI_API_KEY}',
                      customHeaders: headers,
                    })
                    return {
                      ...prev,
                      useAdvancedJson: true,
                      advancedJson: JSON.stringify(json, null, 2),
                    }
                  })
                  setConfigError('')
                }}
              />
            </div>

            {formData.useAdvancedJson && (
              <div className="space-y-2">
                <Textarea
                  id="edit-advancedJson"
                  value={formData.advancedJson}
                  onChange={e => {
                    setFormData(prev => ({ ...prev, advancedJson: e.target.value }))
                    validateJsonObject(e.target.value)
                  }}
                  placeholder={t('admin:public_models.form.config_placeholder')}
                  className={`font-mono text-sm min-h-[220px] bg-base ${
                    configError ? 'border-error' : ''
                  }`}
                />
                {configError && <p className="text-xs text-error">{configError}</p>}
              </div>
            )}

            <div className="flex items-center justify-between">
              <Label htmlFor="edit-is-active">{t('admin:public_models.columns.status')}</Label>
              <div className="flex items-center gap-2">
                <span className="text-sm text-text-muted">
                  {formData.is_active
                    ? t('admin:public_models.status.active')
                    : t('admin:public_models.status.inactive')}
                </span>
                <Switch
                  id="edit-is-active"
                  checked={formData.is_active}
                  onCheckedChange={checked =>
                    setFormData(prev => ({ ...prev, is_active: checked }))
                  }
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              {t('admin:common.cancel')}
            </Button>
            <Button onClick={handleUpdateModel} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('admin:common.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('admin:public_models.confirm.delete_title')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('admin:public_models.confirm.delete_message', { name: selectedModel?.name })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('admin:common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteModel} className="bg-error hover:bg-error/90">
              {t('admin:common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default PublicModelList
