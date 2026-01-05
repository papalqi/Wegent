// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import * as React from 'react';
import { Check, ChevronDown, ChevronRight, ChevronsUpDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

export interface SearchableSelectItem {
  value: string;
  label: string;
  searchText?: string; // Optional custom search text
  disabled?: boolean;
  content?: React.ReactNode; // Custom content for the item
}

export interface SearchableSelectGroup {
  key: string;
  label: string;
  items: SearchableSelectItem[];
  defaultOpen?: boolean;
}

interface SearchableSelectProps {
  value?: string;
  onValueChange?: (value: string) => void;
  onSearchChange?: (value: string) => void; // Callback for search text changes (for server-side search)
  disabled?: boolean;
  placeholder?: string;
  searchPlaceholder?: string;
  items?: SearchableSelectItem[];
  groups?: SearchableSelectGroup[];
  loading?: boolean;
  error?: string | null;
  emptyText?: string;
  noMatchText?: string;
  className?: string;
  contentClassName?: string;
  triggerClassName?: string;
  triggerProps?: React.ButtonHTMLAttributes<HTMLButtonElement>;
  renderTriggerValue?: (item: SearchableSelectItem | undefined) => React.ReactNode;
  footer?: React.ReactNode;
  listFooter?: React.ReactNode; // Content rendered at the end of the list (after items, before footer)
  showChevron?: boolean; // Whether to show chevron icon
  defaultOpen?: boolean; // Whether to open the dropdown by default
}

export function SearchableSelect({
  value,
  onValueChange,
  onSearchChange,
  disabled,
  placeholder = 'Select...',
  searchPlaceholder = 'Search...',
  items = [],
  groups,
  loading,
  error,
  emptyText = 'No items',
  noMatchText = 'No match',
  className,
  contentClassName,
  triggerClassName,
  triggerProps,
  renderTriggerValue,
  footer,
  listFooter,
  showChevron = false,
  defaultOpen = false,
}: SearchableSelectProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen);
  const [searchValue, setSearchValue] = React.useState('');

  const defaultOpenGroupKeys = React.useMemo(() => {
    if (!groups) return new Set<string>();
    return new Set(groups.filter(g => g.defaultOpen).map(g => g.key));
  }, [groups]);

  const [openGroupKeys, setOpenGroupKeys] = React.useState<Set<string>>(defaultOpenGroupKeys);

  React.useEffect(() => {
    setOpenGroupKeys(defaultOpenGroupKeys);
  }, [defaultOpenGroupKeys]);

  const resolvedItems = React.useMemo(() => {
    if (!groups) return items;
    return groups.flatMap(g => g.items);
  }, [groups, items]);

  // Find selected item
  const selectedItem = React.useMemo(() => {
    return resolvedItems.find(item => item.value === value);
  }, [resolvedItems, value]);

  const handleSelect = (currentValue: string) => {
    onValueChange?.(currentValue);
    setIsOpen(false);
  };

  const handleSearchValueChange = (search: string) => {
    setSearchValue(search);
    onSearchChange?.(search);
  };

  // Reset search when popover closes
  React.useEffect(() => {
    if (!isOpen) {
      setSearchValue('');
      onSearchChange?.('');
      setOpenGroupKeys(defaultOpenGroupKeys);
    }
  }, [isOpen, onSearchChange, defaultOpenGroupKeys]);

  React.useEffect(() => {
    if (!groups) return;
    if (!searchValue) return;
    setOpenGroupKeys(new Set(groups.map(g => g.key)));
  }, [groups, searchValue]);

  const toggleGroup = (key: string) => {
    setOpenGroupKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className={className}>
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            role="combobox"
            aria-expanded={isOpen}
            aria-controls="searchable-select-popover"
            disabled={disabled}
            className={cn(
              'flex h-9 w-full min-w-0 items-center justify-between rounded-lg border text-left',
              'border-border bg-base px-3 text-xs text-text-muted',
              'shadow-sm hover:bg-hover transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-primary/20',
              'disabled:cursor-not-allowed disabled:opacity-50',
              triggerClassName
            )}
            {...triggerProps}
          >
            <div className="flex-1 min-w-0">
              {selectedItem && renderTriggerValue ? (
                renderTriggerValue(selectedItem)
              ) : (
                <span className="truncate block">
                  {selectedItem ? selectedItem.label : placeholder}
                </span>
              )}
            </div>
            {showChevron && <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />}
          </button>
        </PopoverTrigger>

        <PopoverContent
          className={cn(
            'p-0 w-auto min-w-[var(--radix-popover-trigger-width)] max-w-[90vw] border border-border bg-base',
            'shadow-xl rounded-xl overflow-hidden',
            'max-h-[var(--radix-popover-content-available-height,400px)]',
            'flex flex-col',
            contentClassName
          )}
          align="start"
          sideOffset={4}
          collisionPadding={8}
          avoidCollisions={true}
          sticky="partial"
        >
          <Command
            className="border-0 flex flex-col flex-1 min-h-0 overflow-hidden"
            shouldFilter={!onSearchChange}
          >
            <CommandInput
              placeholder={searchPlaceholder}
              value={searchValue}
              onValueChange={handleSearchValueChange}
              className={cn(
                'h-9 rounded-none border-b border-border flex-shrink-0',
                'placeholder:text-text-muted text-sm'
              )}
            />
            <CommandList className="min-h-[36px] max-h-[200px] overflow-y-auto flex-1">
              {error ? (
                <div className="py-4 px-3 text-center text-sm text-error">{error}</div>
              ) : resolvedItems.length === 0 ? (
                <CommandEmpty className="py-4 text-center text-sm text-text-muted">
                  {loading ? 'Loading...' : emptyText}
                </CommandEmpty>
              ) : (
                <>
                  {(searchValue || !groups) && (
                    <CommandEmpty className="py-4 text-center text-sm text-text-muted">
                      {noMatchText}
                    </CommandEmpty>
                  )}
                  {groups ? (
                    <div className="py-1">
                      {groups.map(group => {
                        const isGroupOpen = openGroupKeys.has(group.key) || !!searchValue;
                        return (
                          <div key={group.key} className="px-1">
                            <button
                              type="button"
                              className={cn(
                                'w-full flex items-center gap-2 rounded-md px-2 py-1.5',
                                'text-xs font-medium text-text-muted',
                                'hover:bg-hover transition-colors',
                                'focus:outline-none focus:ring-2 focus:ring-primary/20'
                              )}
                              onClick={() => toggleGroup(group.key)}
                              aria-expanded={isGroupOpen}
                            >
                              {isGroupOpen ? (
                                <ChevronDown className="h-4 w-4 shrink-0 opacity-70" />
                              ) : (
                                <ChevronRight className="h-4 w-4 shrink-0 opacity-70" />
                              )}
                              <span className="truncate">{group.label}</span>
                            </button>
                            {isGroupOpen && (
                              <CommandGroup>
                                {group.items.map(item => (
                                  <CommandItem
                                    key={item.value}
                                    value={item.searchText || item.label}
                                    disabled={item.disabled}
                                    onSelect={() => handleSelect(item.value)}
                                    className={cn(
                                      'group cursor-pointer select-none',
                                      'px-3 py-1.5 text-sm text-text-primary',
                                      'rounded-md mx-1 my-[2px]',
                                      'data-[selected=true]:bg-primary/10 data-[selected=true]:text-primary',
                                      'aria-selected:bg-hover',
                                      'data-[disabled=true]:pointer-events-none data-[disabled=true]:opacity-50',
                                      '!flex !flex-row !items-start !gap-3'
                                    )}
                                  >
                                    <Check
                                      className={cn(
                                        'h-3 w-3 shrink-0 mt-0.5 ml-1',
                                        value === item.value
                                          ? 'opacity-100 text-primary'
                                          : 'opacity-0 text-text-muted'
                                      )}
                                    />
                                    {item.content ? (
                                      <div className="flex-1 min-w-0">{item.content}</div>
                                    ) : (
                                      <span className="flex-1 min-w-0 truncate" title={item.label}>
                                        {item.label}
                                      </span>
                                    )}
                                  </CommandItem>
                                ))}
                              </CommandGroup>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <CommandGroup>
                      {items.map(item => (
                        <CommandItem
                          key={item.value}
                          value={item.searchText || item.label}
                          disabled={item.disabled}
                          onSelect={() => handleSelect(item.value)}
                          className={cn(
                            'group cursor-pointer select-none',
                            'px-3 py-1.5 text-sm text-text-primary',
                            'rounded-md mx-1 my-[2px]',
                            'data-[selected=true]:bg-primary/10 data-[selected=true]:text-primary',
                            'aria-selected:bg-hover',
                            'data-[disabled=true]:pointer-events-none data-[disabled=true]:opacity-50',
                            '!flex !flex-row !items-start !gap-3'
                          )}
                        >
                          <Check
                            className={cn(
                              'h-3 w-3 shrink-0 mt-0.5 ml-1',
                              value === item.value
                                ? 'opacity-100 text-primary'
                                : 'opacity-0 text-text-muted'
                            )}
                          />
                          {item.content ? (
                            <div className="flex-1 min-w-0">{item.content}</div>
                          ) : (
                            <span className="flex-1 min-w-0 truncate" title={item.label}>
                              {item.label}
                            </span>
                          )}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  )}
                </>
              )}
            </CommandList>
            {listFooter}
          </Command>
          {footer}
        </PopoverContent>
      </Popover>
    </div>
  );
}
