// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import { apiClient } from './client';

export interface PersistentRepoDirItem {
  relative_path: string;
  repo_dir: string;
  repo_vcs?: string | null;
  is_p4: boolean;
}

export const persistentRepoApis = {
  listDirs: async (params?: {
    q?: string;
    limit?: number;
    depth?: number;
  }): Promise<PersistentRepoDirItem[]> => {
    const query = new URLSearchParams();
    if (params?.q) query.append('q', params.q);
    if (typeof params?.limit === 'number') query.append('limit', String(params.limit));
    if (typeof params?.depth === 'number') query.append('depth', String(params.depth));

    const suffix = query.toString();
    return apiClient.get(`/utils/persistent-repo-dirs${suffix ? `?${suffix}` : ''}`);
  },
};
