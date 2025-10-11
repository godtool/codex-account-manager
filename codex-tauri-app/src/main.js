// Tauri API 导入
import { readTextFile, writeTextFile, readDir, mkdir, exists, remove, stat } from '@tauri-apps/plugin-fs';
import { homeDir, join, appDataDir } from '@tauri-apps/api/path';
import { message, ask, confirm } from '@tauri-apps/plugin-dialog';

// 全局状态
let selectedAccount = null;
let accounts = [];
let isLoading = false;
let PATHS = {};

// =============================================================================
// 工具函数 - Base64URL 解码 (与 Python base64.b64decode 一致)
// =============================================================================

function base64UrlDecode(str) {
    // 添加padding
    const pad = (4 - (str.length % 4)) % 4;
    const b64 = str.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat(pad);
    
    try {
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return new TextDecoder().decode(bytes);
    } catch (e) {
        console.error('Base64 decode error:', e);
        return null;
    }
}

// =============================================================================
// JWT 解析 (与 Python extract_email_from_token 逻辑一致)
// =============================================================================

function parseJwtPayload(token) {
    if (!token || typeof token !== 'string') return null;
    const parts = token.split('.');
    if (parts.length < 2) return null;
    
    try {
        const payload = base64UrlDecode(parts[1]);
        if (!payload) return null;
        return JSON.parse(payload);
    } catch (e) {
        return null;
    }
}

function extractEmailFromToken(config) {
    if (!config || !config.tokens) return null;
    
    // 优先从 id_token 提取
    if (config.tokens.id_token) {
        const payload = parseJwtPayload(config.tokens.id_token);
        if (payload && payload.email) return payload.email;
    }
    
    // 备用：从 access_token 提取
    if (config.tokens.access_token) {
        const payload = parseJwtPayload(config.tokens.access_token);
        if (payload) {
            if (payload.email) return payload.email;
            // OpenAI特定字段
            if (payload['https://api.openai.com/profile']?.email) {
                return payload['https://api.openai.com/profile'].email;
            }
        }
    }
    
    return config.email || null;
}

// =============================================================================
// 路径管理 (与 Python config_utils.get_config_paths 一致)
// =============================================================================

async function initPaths() {
    const home = await homeDir();
    const appData = await appDataDir();
    
    // 系统 Codex 配置路径
    const systemAuthFile = await join(home, '.codex', 'auth.json');
    
    // 应用配置目录（通用，不依赖用户桌面路径）
    const codexConfigDir = await join(appData, 'codex-config');
    
    PATHS = {
        systemAuthFile,
        codexConfigDir,
        accountsDir: await join(codexConfigDir, 'accounts'),
        usageCacheDir: await join(codexConfigDir, 'usage_cache'),
        sessionDir: await join(home, '.codex', 'sessions')
    };
    
    console.log('初始化路径:', PATHS);
}

// =============================================================================
// 目录初始化
// =============================================================================

async function ensureDirs() {
    try {
        await mkdir(PATHS.codexConfigDir, { recursive: true });
        await mkdir(PATHS.accountsDir, { recursive: true });
        await mkdir(PATHS.usageCacheDir, { recursive: true });
        console.log('✅ 目录创建成功');
    } catch (e) {
        console.log('⚠️ 目录已存在或创建失败:', e);
    }
}

// =============================================================================
// JSON 文件读写 (与 Python json.load/dump 一致)
// =============================================================================

async function readJsonSafe(path) {
    try {
        const fileExists = await exists(path);
        if (!fileExists) return null;
        
        const content = await readTextFile(path);
        return JSON.parse(content);
    } catch (e) {
        console.error(`读取JSON失败 ${path}:`, e);
        return null;
    }
}

async function writeJsonSafe(path, data) {
    try {
        const content = JSON.stringify(data, null, 2);
        await writeTextFile(path, content);
        return true;
    } catch (e) {
        console.error(`写入JSON失败 ${path}:`, e);
        throw e;
    }
}

// =============================================================================
// 账号名生成 (与 Python generate_account_name 一致)
// =============================================================================

function generateAccountName(email) {
    if (!email) return `account_${Date.now()}`;
    const username = email.split('@')[0];
    return username.replace(/[^a-zA-Z0-9._-]/g, '_');
}

// =============================================================================
// 账号加载 (与 Python get_accounts_data 一致)
// =============================================================================

async function loadAccounts() {
    try {
        console.log('📂 开始加载账号，目录:', PATHS.accountsDir);
        const entries = await readDir(PATHS.accountsDir);
        console.log('📋 找到', entries.length, '个文件/目录');
        accounts = [];
        
        // 获取当前账号邮箱
        let currentEmail = null;
        const currentConfig = await readJsonSafe(PATHS.systemAuthFile);
        if (currentConfig) {
            currentEmail = extractEmailFromToken(currentConfig);
            console.log('当前账号邮箱:', currentEmail);
        } else {
            console.log('未找到系统auth文件');
        }
        
        // 读取所有账号配置
        for (const entry of entries) {
            if (entry.name && entry.name.endsWith('.json')) {
                const filePath = await join(PATHS.accountsDir, entry.name);
                const config = await readJsonSafe(filePath);
                
                if (config) {
                    const accountName = entry.name.replace('.json', '');
                    const email = extractEmailFromToken(config) || '未知';
                    const planType = extractPlanType(config) || '未知';
                    const savedAt = config.saved_at || '未知时间';
                    const isCurrent = currentEmail && email === currentEmail;
                    
                    console.log(`账号: ${accountName}, Email: ${email}, 是否当前: ${isCurrent}`);
                    
                    accounts.push({
                        name: accountName,
                        email,
                        plan: planType,
                        saved_at: formatDate(savedAt),
                        is_current: isCurrent,
                        path: filePath,
                        config
                    });
                }
            }
        }
        
        // 排序：当前账号在前
        accounts.sort((a, b) => {
            if (a.is_current && !b.is_current) return -1;
            if (!a.is_current && b.is_current) return 1;
            return a.name.localeCompare(b.name);
        });
        
        console.log(`✅ 加载了 ${accounts.length} 个账号:`, accounts.map(a => `${a.name}(当前:${a.is_current})`).join(', '));
        renderAccounts();
    } catch (e) {
        console.error('加载账号失败:', e);
        showMessage('加载账号列表失败: ' + e, 'error');
    }
}

// =============================================================================
// 提取套餐类型
// =============================================================================

function extractPlanType(config) {
    try {
        if (!config || !config.tokens || !config.tokens.access_token) return null;
        
        const payload = parseJwtPayload(config.tokens.access_token);
        if (payload && payload['https://api.openai.com/auth']) {
            return payload['https://api.openai.com/auth'].chatgpt_plan_type;
        }
    } catch (e) {
        // ignore
    }
    return null;
}

// =============================================================================
// 时间格式化
// =============================================================================

function formatDate(dateStr) {
    try {
        if (dateStr === '未知时间') return dateStr;
        const date = new Date(dateStr);
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${month}-${day} ${hours}:${minutes}`;
    } catch (e) {
        return dateStr;
    }
}

// =============================================================================
// UI 渲染
// =============================================================================

function renderAccounts() {
    const tbody = document.getElementById('accounts-list');
    const emptyState = document.getElementById('empty-state');
    const accountCountEl = document.getElementById('account-count');
    
    // 更新账号计数
    accountCountEl.textContent = `共 ${accounts.length} 个账号`;
    
    if (accounts.length === 0) {
        tbody.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }
    
    tbody.style.display = '';
    emptyState.style.display = 'none';
    
    console.log('🎨 开始渲染', accounts.length, '个账号');
    
    tbody.innerHTML = accounts.map(account => {
        console.log(`渲染账号 ${account.name}: is_current=${account.is_current}`);
        const rowClass = account.is_current ? 'current-row' : '';
        return `
        <tr class="${rowClass}" data-account="${account.name}" onclick="selectRow('${account.name}')">
            <td>
                ${account.is_current ? '<span class="status-indicator current"></span>' : ''}
            </td>
            <td class="account-name-cell">${account.name}</td>
            <td class="account-email-cell">${account.email}</td>
            <td class="account-plan-cell">
                <span class="plan-badge ${getPlanClass(account.plan)}">${account.plan}</span>
            </td>
            <td class="usage-cell" id="usage-primary-${account.name}">
                <span class="usage-text">-</span>
            </td>
            <td class="usage-cell" id="usage-secondary-${account.name}">
                <span class="usage-text">-</span>
            </td>
            <td class="time-cell">${account.saved_at}</td>
            <td>
                <div class="actions-cell">
                    <button class="btn-secondary" onclick="handleSwitchClick(event, '${account.name}')" title="切换到此账号">
                        切换
                    </button>
                    <button class="btn-primary" ${account.is_current ? '' : 'disabled'} onclick="handleRefreshClick(event, '${account.name}')" title="${account.is_current ? '刷新用量数据' : '仅当前账号可刷新'}">
                        刷新
                    </button>
                    <button class="btn-danger" onclick="handleDeleteClick(event, '${account.name}')" title="${account.is_current ? '当前账号请先切换后再删除' : '删除此账号'}">
                        删除
                    </button>
                </div>
            </td>
        </tr>
        `;
    }).join('');
    
    // 延迟加载用量信息
    accounts.forEach((account, index) => {
        setTimeout(() => loadAccountUsage(account.name), index * 100);
    });
}

function getPlanClass(plan) {
    if (!plan || plan === '未知') return '';
    const planLower = plan.toLowerCase();
    if (planLower.includes('plus')) return 'plus';
    if (planLower.includes('pro')) return 'pro';
    return '';
}

function selectRow(accountName) {
    document.querySelectorAll('.accounts-table tbody tr').forEach(row => {
        row.classList.remove('selected-row');
    });
    
    const row = document.querySelector(`tr[data-account="${accountName}"]`);
    if (row) {
        row.classList.add('selected-row');
        selectedAccount = accountName;
    }
}

// 按钮点击处理函数 - 确保事件正确阻止
function handleSwitchClick(event, accountName) {
    event.stopPropagation();
    event.preventDefault();
    quickSwitchAccount(accountName);
}

function handleDeleteClick(event, accountName) {
    event.stopPropagation();
    event.preventDefault();
    quickDeleteAccount(accountName);
}

function handleRefreshClick(event, accountName) {
    event.stopPropagation();
    event.preventDefault();
    refreshCurrentAccountUsage(accountName);
}


// =============================================================================
// 账号操作 (与 Python 逻辑一致)
// =============================================================================

// 快速保存当前账号
async function quickSave() {
    try {
        setButtonLoading('quick-save-btn', true);
        showMessage('正在备份当前账号...', 'success');
        
        const config = await readJsonSafe(PATHS.systemAuthFile);
        if (!config) {
            throw new Error('未找到当前系统认证文件');
        }
        
        const email = extractEmailFromToken(config);
        if (!email) {
            throw new Error('无法从配置中提取邮箱信息');
        }
        
        const accountName = generateAccountName(email);
        config.saved_at = new Date().toISOString();
        config.account_name = accountName;
        config.email = email;
        
        const accountFile = await join(PATHS.accountsDir, `${accountName}.json`);
        await writeJsonSafe(accountFile, config);
        
        showMessage(`成功保存账号: ${accountName} (${email})`, 'success');
        await loadAccounts();
    } catch (e) {
        showMessage('保存账号失败: ' + e.message, 'error');
    } finally {
        setButtonLoading('quick-save-btn', false);
    }
}

// 快速切换账号
async function quickSwitchAccount(accountName) {
    console.log('🔄 准备切换到账号:', accountName);
    console.log('当前accounts数组:', accounts);
    
    const confirmed = await confirm(`确定要切换到账号 '${accountName}' 吗？`, {
        title: '确认切换',
        type: 'warning',
        okLabel: '确定',
        cancelLabel: '取消'
    });
    
    if (!confirmed) {
        console.log('用户取消切换');
        return;
    }
    
    try {
        showMessage(`正在切换到账号 ${accountName}...`, 'success');
        
        const account = accounts.find(a => a.name === accountName);
        console.log('找到账号对象:', account);
        
        if (!account) {
            throw new Error('账号不存在');
        }
        
        if (!account.config) {
            console.error('账号config为空:', account);
            throw new Error('账号配置为空');
        }
        
        console.log('账号配置:', account.config);
        
        // 清理配置只保留必要字段 (与Python一致)
        const cleanConfig = {
            OPENAI_API_KEY: account.config.OPENAI_API_KEY,
            tokens: account.config.tokens,
            last_refresh: account.config.last_refresh
        };
        
        console.log('准备写入系统配置:', PATHS.systemAuthFile);
        await writeJsonSafe(PATHS.systemAuthFile, cleanConfig);
        console.log('✅ 系统配置写入成功');
        
        showMessage(`成功切换到账号: ${accountName}`, 'success');
        selectedAccount = null;
        
        setTimeout(() => {
            loadAccounts();
            showMessage(`已切换到账号 ${accountName}，请用 codex 发送消息后刷新用量`, 'success');
        }, 1000);
    } catch (e) {
        console.error('❌ 切换账号错误:', e);
        showMessage('切换账号失败: ' + (e.message || String(e)), 'error');
    }
}

// 快速删除账号
async function quickDeleteAccount(accountName) {
    const confirmed = await confirm(
        `确定要删除账号 '${accountName}' 吗？\n\n此操作不可恢复！`,
        {
            title: '确认删除',
            type: 'warning',
            okLabel: '删除',
            cancelLabel: '取消'
        }
    );
    
    if (!confirmed) {
        return;
    }
    
    try {
        const account = accounts.find(a => a.name === accountName);
        if (!account) return;

        // 防止删除当前账号
        if (account.is_current) {
            showMessage('当前账号不可删除，请先切换到其他账号后再删除', 'error');
            return;
        }

        await remove(account.path);
        
        showMessage(`成功删除账号: ${accountName}`, 'success');
        if (selectedAccount === accountName) {
            selectedAccount = null;
        }
        await loadAccounts();
    } catch (e) {
        showMessage('删除账号失败: ' + e.message, 'error');
    }
}


// =============================================================================
// 用量查询功能 (完整实现)
// =============================================================================

// 查找最新的 session 文件
async function findLatestSessionFile() {
    try {
        const sessionDir = PATHS.sessionDir;
        const sessionExists = await exists(sessionDir);
        if (!sessionExists) return null;

        // 递归查找所有 rollout-*.jsonl 文件
        const files = await findRolloutFiles(sessionDir);
        console.log('🧾 session 文件数量:', files.length);
        if (files.length > 0) {
            console.log('🧾 最近候选文件(前3):', files.slice(0, 3).map(f => f.path));
        }
        if (files.length === 0) return null;

        // 按修改时间排序（最新的在前）
        files.sort((a, b) => b.mtime - a.mtime);

        // 检查最近10个文件，找到包含 token_count 数据的
        for (const file of files.slice(0, 10)) {
            if (await hasTokenCountData(file.path)) {
                console.log('✅ 选用含 token_count 的文件:', file.path);
                return file.path;
            }
        }

        console.log('⚠️ 未找到包含 token_count 的文件，回退到最新文件:', files[0]?.path);
        return files[0]?.path || null;
    } catch (e) {
        console.error('查找 session 文件失败:', e);
        return null;
    }
}

// 递归查找 rollout-*.jsonl 文件
async function findRolloutFiles(dir) {
  const result = [];
  try {
    const entries = await readDir(dir);
    for (const entry of entries) {
      const fullPath = await join(dir, entry.name);
      if (entry.isDirectory) {
        // 递归查找子目录
        const subFiles = await findRolloutFiles(fullPath);
        result.push(...subFiles);
      } else if (entry.name.startsWith('rollout-') && entry.name.endsWith('.jsonl')) {
        // 这是我们要找的文件，读取真实修改时间用于排序（与 Python 一致）
        let mtime = 0;
        try {
          const info = await stat(fullPath);
          // 兼容不同字段命名
          if (typeof info.mtimeMs === 'number') mtime = info.mtimeMs;
          else if (typeof info.modifiedAt === 'number') mtime = info.modifiedAt;
          else if (info.mtime) mtime = Number(info.mtime) || 0;
        } catch (_) {
          mtime = 0;
        }
        result.push({ path: fullPath, mtime });
      }
    }
  } catch (e) {
    // 忽略权限错误
  }
  return result.sort((a, b) => b.mtime - a.mtime);
}

// 检查文件是否包含 token_count 数据
async function hasTokenCountData(filePath) {
    try {
        const content = await readTextFile(filePath);
        const lines = content.split('\n').filter(line => line.trim());
        // 只检查最后20行
        const lastLines = lines.slice(-20);
        for (const line of lastLines.reverse()) {
            try {
                const data = JSON.parse(line);
                if (data.payload?.type === 'token_count') {
                    return true;
                }
            } catch (e) {
                continue;
            }
        }
        return false;
    } catch (e) {
        return false;
    }
}

// 解析 session 文件获取用量数据
async function parseSessionFile(filePath) {
    try {
        const content = await readTextFile(filePath);
        const lines = content.split('\n').filter(line => line.trim());
        
        // 从后往前查找最新的 token_count 事件
        for (const line of lines.reverse()) {
            try {
                const data = JSON.parse(line);
                const payload = data.payload;
                if (payload?.type === 'token_count' && payload.rate_limits) {
                    return data;
                }
            } catch (e) {
                continue;
            }
        }
        return null;
    } catch (e) {
        console.error('解析 session 文件失败:', e);
        return null;
    }
}

// 加载缓存的用量数据
async function loadCachedUsage(email) {
    if (!email) return null;
    
    try {
        const safeEmail = email.replace(/@/g, '_at_').replace(/\./g, '_').replace(/\+/g, '_plus_');
        const cacheFile = await join(PATHS.usageCacheDir, `${safeEmail}_usage.json`);
        const cacheExists = await exists(cacheFile);
        
        if (!cacheExists) return null;
        
        const cacheData = await readJsonSafe(cacheFile);
        if (!cacheData) return null;
        
        // 检查是否过期（30天）
        const lastUpdated = new Date(cacheData.last_updated);
        const now = new Date();
        const daysDiff = (now - lastUpdated) / (1000 * 60 * 60 * 24);
        
        if (daysDiff > 30) return null;
        
        return cacheData.usage_data;
    } catch (e) {
        return null;
    }
}

// 保存用量数据到缓存
async function saveCachedUsage(email, usageData) {
    if (!email || !usageData) return false;
    
    try {
        const safeEmail = email.replace(/@/g, '_at_').replace(/\./g, '_').replace(/\+/g, '_plus_');
        const cacheFile = await join(PATHS.usageCacheDir, `${safeEmail}_usage.json`);
        
        const cacheData = {
            email,
            last_updated: new Date().toISOString(),
            usage_data: usageData
        };
        
        await writeJsonSafe(cacheFile, cacheData);
        return true;
    } catch (e) {
        console.error('保存缓存失败:', e);
        return false;
    }
}

// 获取用量摘要
async function getUsageSummary(email) {
    const summary = {
        check_time: new Date().toLocaleString('zh-CN'),
        status: 'checking',
        token_usage: {},
        rate_limits: {},
        errors: []
    };
    
    const sessionFile = await findLatestSessionFile();
    if (!sessionFile) {
        summary.errors.push('未找到 Codex CLI session 文件');
        summary.status = 'failed';
        return summary;
    }
    console.log('📄 使用的 session 文件:', sessionFile);
    
    const tokenData = await parseSessionFile(sessionFile);
    if (!tokenData) {
        summary.errors.push('未找到有效的用量数据，请先使用 codex 发送消息');
        summary.status = 'failed';
        return summary;
    }
    
    const payload = tokenData.payload;
    const info = payload.info;
    
    if (info && info.total_token_usage) {
        summary.token_usage = info.total_token_usage;
    }
    
    if (payload.rate_limits) {
        summary.rate_limits = payload.rate_limits;
    }
    
    summary.status = 'success';
    
    // 保存到缓存
    if (email && summary.status === 'success') {
        await saveCachedUsage(email, {
            check_time: summary.check_time,
            token_usage: summary.token_usage,
            rate_limits: summary.rate_limits
        });
    }
    
    return summary;
}

// 格式化用量单元格 HTML
function formatUsageCell(percent, resetInfo, fromCache = false) {
    if (percent === null || percent === undefined) {
        return '<span class="usage-text" style="color: var(--text-muted);">-</span>';
    }
    
    const barClass = percent > 80 ? 'high' : percent > 60 ? 'medium' : 'low';
    const cacheIndicator = fromCache ? ' <span class="cache-badge" title="缓存数据">缓存</span>' : '';
    
    return `
        <div class="usage-indicator">
            <div class="usage-bar-mini">
                <div class="usage-bar-fill ${barClass}" style="width: ${percent}%;"></div>
            </div>
            <span class="usage-text">${percent}%${cacheIndicator}</span>
        </div>
        ${resetInfo ? `<div class="usage-reset">${resetInfo}</div>` : ''}
    `;
}

// 加载账号用量 (表格版本)
async function loadAccountUsage(accountName) {
    const primaryCell = document.getElementById(`usage-primary-${accountName}`);
    const secondaryCell = document.getElementById(`usage-secondary-${accountName}`);
    
    if (!primaryCell || !secondaryCell) return;
    
    const account = accounts.find(a => a.name === accountName);
    if (!account) return;
    
    try {
        // 所有账号都首先尝试从缓存读取
        const cachedUsage = await loadCachedUsage(account.email);
        
        if (cachedUsage) {
            // 使用缓存数据
            const primary = cachedUsage.rate_limits?.primary;
            const secondary = cachedUsage.rate_limits?.secondary;
            
            if (primary) {
                const percent = parseInt(primary.used_percent) || 0;
                const resetTime = new Date(Date.now() + (primary.resets_in_seconds || 0) * 1000);
                const resetInfo = resetTime.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
                primaryCell.innerHTML = formatUsageCell(percent, resetInfo, true);
            }
            
            if (secondary) {
                const percent = parseInt(secondary.used_percent) || 0;
                const resetTime = new Date(Date.now() + (secondary.resets_in_seconds || 0) * 1000);
                const resetInfo = `${resetTime.toLocaleDateString('zh-CN', {month: '2-digit', day: '2-digit'})} ${resetTime.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})}`;
                secondaryCell.innerHTML = formatUsageCell(percent, resetInfo, true);
            }
        } else {
            // 只有当前账号才会尝试实时查询
            if (account.is_current) {
                const summary = await getUsageSummary(account.email);
                if (summary.status === 'success' && summary.rate_limits) {
                    const primary = summary.rate_limits.primary;
                    const secondary = summary.rate_limits.secondary;
                    
                    if (primary) {
                        const percent = parseInt(primary.used_percent) || 0;
                        const resetTime = new Date(Date.now() + (primary.resets_in_seconds || 0) * 1000);
                        const resetInfo = resetTime.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
                        primaryCell.innerHTML = formatUsageCell(percent, resetInfo, false);
                    }
                    
                    if (secondary) {
                        const percent = parseInt(secondary.used_percent) || 0;
                        const resetTime = new Date(Date.now() + (secondary.resets_in_seconds || 0) * 1000);
                        const resetInfo = `${resetTime.toLocaleDateString('zh-CN', {month: '2-digit', day: '2-digit'})} ${resetTime.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})}`;
                        secondaryCell.innerHTML = formatUsageCell(percent, resetInfo, false);
                    }
                } else {
                    primaryCell.innerHTML = '<span class="usage-text" style="color: var(--warning);">无数据</span>';
                    secondaryCell.innerHTML = '<span class="usage-text" style="color: var(--warning);">无数据</span>';
                }
            } else {
                primaryCell.innerHTML = '<span class="usage-text" style="color: var(--text-muted);">-</span>';
                secondaryCell.innerHTML = '<span class="usage-text" style="color: var(--text-muted);">-</span>';
            }
        }
    } catch (error) {
        primaryCell.innerHTML = '<span class="usage-text" style="color: var(--danger);">错误</span>';
        secondaryCell.innerHTML = '<span class="usage-text" style="color: var(--danger);">错误</span>';
    }
}

// 刷新当前账号用量 (与Web端一致)
async function refreshCurrentAccountUsage(accountName) {
    const account = accounts.find(a => a.name === accountName);
    if (!account || !account.is_current) {
        showMessage('只能刷新当前账号的用量', 'error');
        return;
    }
    
    try {
        showMessage(`正在刷新账号 ${accountName} 的用量数据...`, 'success');
        
        // 从session读取最新用量
        const summary = await getUsageSummary(account.email);
        
        if (summary.status === 'success') {
            showMessage(`已刷新账号 ${account.email} 的用量数据`, 'success');
            // 刷新成功后重新加载用量显示
            setTimeout(() => {
                loadAccountUsage(accountName);
            }, 500);
        } else {
            const errorMsg = summary.errors?.[0] || '未知错误';
            showMessage(`刷新失败: ${errorMsg}`, 'error');
        }
    } catch (error) {
        showMessage('刷新失败: ' + error.message, 'error');
    }
}

// =============================================================================
// UI 辅助函数
// =============================================================================

function showMessage(message, type = 'success') {
    const messageArea = document.getElementById('message-area');
    const icon = type === 'success' ? '[成功]' : '[错误]';
    const alertClass = type === 'success' ? 'alert-success' : 'alert-error';
    
    const toast = document.createElement('div');
    toast.className = `toast ${alertClass}`;
    toast.innerHTML = `${icon} ${message}`;
    
    messageArea.innerHTML = '';
    messageArea.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease-out reverse';
        setTimeout(() => {
            if (messageArea.contains(toast)) {
                messageArea.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

function setButtonLoading(buttonId, loading) {
    const button = document.getElementById(buttonId);
    if (!button) return;
    
    if (loading) {
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        const icon = button.querySelector('.btn-icon');
        const text = button.querySelector('span:not(.btn-icon)');
        if (icon && text) {
            icon.textContent = '⏳';
            text.textContent = '处理中';
        }
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalText || button.innerHTML;
    }
}

function refreshData() {
    if (!isLoading) {
        selectedAccount = null;
        loadAccounts();
    }
}

// =============================================================================
// 初始化应用
// =============================================================================

async function initApp() {
    try {
        console.log('🚀 初始化 Tauri 应用...');
        await initPaths();
        await ensureDirs();
        await loadAccounts();
        console.log('✅ 应用初始化完成');
    } catch (e) {
        console.error('初始化失败:', e);
        showMessage('应用初始化失败: ' + e.message, 'error');
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initApp);

// 导出全局函数供 HTML 调用
window.quickSave = quickSave;
window.quickSwitchAccount = quickSwitchAccount;
window.quickDeleteAccount = quickDeleteAccount;
window.selectRow = selectRow;
window.refreshCurrentAccountUsage = refreshCurrentAccountUsage;
window.refreshData = refreshData;
window.handleSwitchClick = handleSwitchClick;
window.handleDeleteClick = handleDeleteClick;
window.handleRefreshClick = handleRefreshClick;
