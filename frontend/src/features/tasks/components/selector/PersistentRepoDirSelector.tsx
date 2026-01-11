// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, ChevronRight, FolderOpen, RefreshCw } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Tag } from '@/components/ui/tag';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { useTranslation } from '@/hooks/useTranslation';
import { persistentRepoApis, type PersistentRepoDirItem } from '@/apis/persistent-repo';

interface DirTreeNode {
  name: string;
  relativePath: string;
  repoDir: string;
  repoVcs?: string | null;
  isP4: boolean;
  children: Map<string, DirTreeNode>;
}

interface PersistentRepoDirSelectorProps {
  value?: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
  compact?: boolean;
}

function buildDirTree(items: PersistentRepoDirItem[]): DirTreeNode[] {
  const mountPrefix = '/wegent_repos';
  const meta = new Map<string, PersistentRepoDirItem>();
  for (const item of items) meta.set(item.relative_path, item);

  const rootChildren = new Map<string, DirTreeNode>();

  const getOrCreate = (parent: Map<string, DirTreeNode>, name: string, relativePath: string) => {
    const existing = parent.get(name);
    if (existing) return existing;

    const metaItem = meta.get(relativePath);
    const node: DirTreeNode = {
      name,
      relativePath,
      repoDir: metaItem?.repo_dir || `${mountPrefix}/${relativePath}`,
      repoVcs: metaItem?.repo_vcs ?? null,
      isP4: metaItem?.is_p4 ?? false,
      children: new Map<string, DirTreeNode>(),
    };
    parent.set(name, node);
    return node;
  };

  for (const item of items) {
    const parts = item.relative_path.split('/').filter(Boolean);
    let currentMap = rootChildren;
    let currentPath = '';
    for (const part of parts) {
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const node = getOrCreate(currentMap, part, currentPath);
      currentMap = node.children;
    }
  }

  const sortChildren = (nodes: DirTreeNode[]): DirTreeNode[] => {
    const sorted = [...nodes].sort((a, b) => a.name.localeCompare(b.name));
    for (const node of sorted) {
      node.children = new Map(
        sortChildren(Array.from(node.children.values())).map(child => [child.name, child])
      );
    }
    return sorted;
  };

  return sortChildren(Array.from(rootChildren.values()));
}

function flattenTree(
  nodes: DirTreeNode[],
  expandedKeys: Set<string>
): Array<{ node: DirTreeNode; depth: number; hasChildren: boolean; expanded: boolean }> {
  const rows: Array<{ node: DirTreeNode; depth: number; hasChildren: boolean; expanded: boolean }> =
    [];

  const walk = (nodeList: DirTreeNode[], depth: number) => {
    for (const node of nodeList) {
      const hasChildren = node.children.size > 0;
      const expanded = expandedKeys.has(node.relativePath);
      rows.push({ node, depth, hasChildren, expanded });
      if (hasChildren && expanded) {
        walk(Array.from(node.children.values()), depth + 1);
      }
    }
  };

  walk(nodes, 0);
  return rows;
}

export default function PersistentRepoDirSelector({
  value = '',
  onChange,
  disabled = false,
  compact = false,
}: PersistentRepoDirSelectorProps) {
  const { toast } = useToast();
  const { t } = useTranslation();

  const [open, setOpen] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [dirs, setDirs] = useState<PersistentRepoDirItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());
  const debounceRef = useRef<NodeJS.Timeout | null>(null);
  const skipNextSearchEffectRef = useRef(false);
  const requestIdRef = useRef(0);

  const selectedValue = useMemo(() => value.trim(), [value]);
  const tree = useMemo(() => buildDirTree(dirs), [dirs]);
  const rows = useMemo(() => flattenTree(tree, expandedKeys), [tree, expandedKeys]);

  const loadDirs = useCallback(
    async (query: string) => {
      const queryTrimmed = query.trim();
      const requestId = ++requestIdRef.current;
      setLoading(true);
      setError(null);
      try {
        const data = await persistentRepoApis.listDirs({
          q: queryTrimmed,
          depth: 3,
          limit: 300,
        });
        if (requestId !== requestIdRef.current) return;
        setDirs(data);
        if (queryTrimmed) {
          const expanded = new Set<string>();
          const stack: DirTreeNode[] = [...buildDirTree(data)];
          while (stack.length > 0) {
            const node = stack.pop();
            if (!node) break;
            if (node.children.size > 0) expanded.add(node.relativePath);
            for (const child of node.children.values()) stack.push(child);
          }
          setExpandedKeys(expanded);
        }
      } catch {
        if (requestId !== requestIdRef.current) return;
        setDirs([]);
        setError(t('common:tasks.code_workspace_dir_load_failed'));
        toast({
          variant: 'destructive',
          title: t('common:tasks.code_workspace_dir_load_failed'),
        });
      } finally {
        if (requestId === requestIdRef.current) setLoading(false);
      }
    },
    [t, toast]
  );

  useEffect(() => {
    if (!open) {
      setSearchValue('');
      setError(null);
      setExpandedKeys(new Set());
      skipNextSearchEffectRef.current = false;
      return;
    }
    setExpandedKeys(new Set());
    skipNextSearchEffectRef.current = true;
    loadDirs('');
  }, [open, loadDirs]);

  useEffect(() => {
    if (!open) return;
    if (skipNextSearchEffectRef.current) {
      skipNextSearchEffectRef.current = false;
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const query = searchValue.trim();
    if (!query) setExpandedKeys(new Set());
    debounceRef.current = setTimeout(() => {
      loadDirs(query);
    }, 250);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [open, searchValue, loadDirs]);

  const handleSelectNode = useCallback(
    (node: DirTreeNode) => {
      onChange?.(node.relativePath);
      setOpen(false);
    },
    [onChange]
  );

  const toggleExpanded = useCallback((key: string) => {
    setExpandedKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const triggerDisabled = disabled || !onChange;

  return (
    <div className="flex items-center gap-1">
      <Input
        value={value}
        onChange={e => onChange?.(e.target.value)}
        disabled={triggerDisabled}
        placeholder={t('common:tasks.code_workspace_dir_placeholder')}
        className={cn('h-8 px-3 py-1 text-sm bg-surface', compact ? 'w-40' : 'w-64')}
      />

      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            className={cn(
              'h-8 w-8 rounded-lg border border-border bg-base',
              'flex items-center justify-center',
              'hover:bg-hover transition-colors',
              'disabled:cursor-not-allowed disabled:opacity-50'
            )}
            title={t('common:tasks.code_workspace_dir_select')}
            disabled={triggerDisabled}
          >
            <FolderOpen className="h-4 w-4 text-text-muted" />
          </button>
        </PopoverTrigger>
        <PopoverContent
          className={cn(
            'p-0 w-[360px] max-w-[90vw] border border-border bg-base',
            'shadow-xl rounded-xl overflow-hidden',
            'max-h-[var(--radix-popover-content-available-height,420px)]',
            'flex flex-col'
          )}
          align="start"
          sideOffset={4}
          collisionPadding={8}
          avoidCollisions={true}
          sticky="partial"
        >
          <div className="flex items-center gap-2 px-2 py-2 border-b border-border">
            <span className="text-xs font-medium text-text-muted">
              {t('common:tasks.code_workspace_dir_select')}
            </span>
            <button
              type="button"
              className={cn(
                'ml-auto h-7 w-7 rounded-md border border-border bg-base',
                'flex items-center justify-center',
                'hover:bg-hover transition-colors',
                'disabled:cursor-not-allowed disabled:opacity-50'
              )}
              title={t('common:tasks.code_workspace_dir_refresh')}
              onClick={() => loadDirs(searchValue.trim())}
              disabled={loading}
            >
              <RefreshCw className={cn('h-3.5 w-3.5', loading ? 'animate-spin' : '')} />
            </button>
          </div>

          <Command
            className="border-0 flex flex-col flex-1 min-h-0 overflow-hidden"
            shouldFilter={false}
          >
            <CommandInput
              placeholder={t('common:tasks.code_workspace_dir_search_placeholder')}
              value={searchValue}
              onValueChange={setSearchValue}
              className={cn(
                'h-9 rounded-none border-b border-border flex-shrink-0',
                'placeholder:text-text-muted text-sm'
              )}
            />
            <CommandList className="min-h-[36px] max-h-[260px] overflow-y-auto flex-1">
              {error ? (
                <div className="py-4 px-3 text-center text-sm text-error">{error}</div>
              ) : rows.length === 0 ? (
                <CommandEmpty className="py-4 text-center text-sm text-text-muted">
                  {loading ? 'Loading...' : t('common:tasks.code_workspace_dir_empty')}
                </CommandEmpty>
              ) : (
                <>
                  <CommandEmpty className="py-4 text-center text-sm text-text-muted">
                    {t('common:branches.no_match')}
                  </CommandEmpty>
                  <CommandGroup>
                    {rows.map(({ node, depth, hasChildren, expanded }) => {
                      const isSelected =
                        selectedValue === node.relativePath || selectedValue === node.repoDir;
                      const leftPadding = 10 + depth * 16;
                      return (
                        <CommandItem
                          key={node.relativePath}
                          value={node.relativePath}
                          onSelect={() => handleSelectNode(node)}
                          className={cn(
                            'group cursor-pointer select-none',
                            'px-3 py-2 text-sm text-text-primary',
                            'rounded-md mx-1 my-[2px]',
                            'data-[selected=true]:bg-primary/10 data-[selected=true]:text-primary',
                            'aria-selected:bg-hover',
                            '!flex !flex-row !items-start !justify-between !gap-2'
                          )}
                        >
                          <div className="flex flex-col min-w-0 flex-1 gap-1">
                            <div className="flex items-center gap-2 min-w-0">
                              <div
                                className="flex items-center gap-1.5 min-w-0"
                                style={{ paddingLeft: leftPadding }}
                              >
                                {hasChildren ? (
                                  <button
                                    type="button"
                                    className={cn(
                                      'h-5 w-5 rounded-md flex items-center justify-center',
                                      'hover:bg-hover transition-colors',
                                      'text-text-muted'
                                    )}
                                    onClick={e => {
                                      e.preventDefault();
                                      e.stopPropagation();
                                      toggleExpanded(node.relativePath);
                                    }}
                                    aria-label={expanded ? 'Collapse' : 'Expand'}
                                  >
                                    {expanded ? (
                                      <ChevronDown className="h-4 w-4" />
                                    ) : (
                                      <ChevronRight className="h-4 w-4" />
                                    )}
                                  </button>
                                ) : (
                                  <span className="h-5 w-5" />
                                )}
                                <span className="truncate text-sm" title={node.relativePath}>
                                  {node.name}
                                </span>
                              </div>
                              {node.repoVcs === 'git' && (
                                <Tag variant="info" className="text-[10px] flex-shrink-0">
                                  Git
                                </Tag>
                              )}
                              {node.repoVcs === 'p4' && (
                                <Tag variant="warning" className="text-[10px] flex-shrink-0">
                                  P4
                                </Tag>
                              )}
                            </div>
                            <span
                              className="text-xs text-text-muted truncate"
                              title={node.repoDir}
                              style={{ paddingLeft: leftPadding + 22 }}
                            >
                              {node.repoDir}
                            </span>
                          </div>
                          <Check
                            className={cn(
                              'h-3.5 w-3.5 shrink-0 mt-0.5',
                              isSelected ? 'opacity-100 text-primary' : 'opacity-0'
                            )}
                          />
                        </CommandItem>
                      );
                    })}
                  </CommandGroup>
                </>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}
