// SPDX-FileCopyrightText: 2025 WeCode, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import React, { useMemo, useState } from 'react';
import { Check, Copy } from 'lucide-react';

import type { Team } from '@/types/api';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
import { useTranslation } from '@/hooks/useTranslation';
import { cn } from '@/lib/utils';

type SystemPromptPanelProps = {
  team?: Team | null;
  className?: string;
};

export default function SystemPromptPanel({ team, className }: SystemPromptPanelProps) {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [copied, setCopied] = useState(false);

  const promptText = useMemo(() => {
    const bots = team?.bots ?? [];
    if (!bots.length) return '';

    const hasMultipleBots = bots.length > 1;
    const pieces = bots
      .map(bot => {
        const prompt = (bot.bot_prompt ?? '').trim();
        if (!prompt) return null;

        if (!hasMultipleBots) return prompt;

        const roleLabel = bot.role || `Bot ${bot.bot_id}`;
        return `# ${roleLabel}\n\n${prompt}`;
      })
      .filter((v): v is string => Boolean(v));

    return pieces.join('\n\n---\n\n');
  }, [team?.bots]);

  if (!team) return null;

  const hasPrompt = Boolean(promptText.trim());

  const handleCopy = async () => {
    if (!hasPrompt) return;

    try {
      if (
        typeof navigator !== 'undefined' &&
        navigator.clipboard &&
        navigator.clipboard.writeText
      ) {
        await navigator.clipboard.writeText(promptText);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = promptText;
        textarea.style.cssText = 'position:fixed;opacity:0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }

      setCopied(true);
      toast({ title: t('chat:messages.copied') || 'Copied to clipboard' });
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy system prompt:', error);
      toast({
        variant: 'destructive',
        title: t('chat:messages.failed_to_copy') || 'Failed to copy',
      });
    }
  };

  return (
    <Card className={cn('mb-4', className)} padding="sm">
      <Accordion type="single" collapsible>
        <AccordionItem value="system-prompt" className="border-none">
          <AccordionTrigger className="py-1 text-sm font-medium hover:no-underline">
            {t('chat:settings.system_prompt') || 'System Prompt'}
          </AccordionTrigger>
          <AccordionContent className="pb-0 pt-2">
            <div className="flex items-center justify-end pb-2">
              <Button size="sm" variant="outline" onClick={handleCopy} disabled={!hasPrompt}>
                {copied ? (
                  <Check className="mr-2 h-4 w-4 text-green-500" />
                ) : (
                  <Copy className="mr-2 h-4 w-4" />
                )}
                {t('chat:actions.copy') || 'Copy'}
              </Button>
            </div>

            <ScrollArea className="max-h-64 rounded-md border bg-muted/20">
              <pre className="p-3 text-xs font-mono whitespace-pre-wrap break-words text-text-primary">
                {hasPrompt
                  ? promptText
                  : t('chat:settings.system_prompt_empty') || 'No system prompt'}
              </pre>
            </ScrollArea>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </Card>
  );
}
