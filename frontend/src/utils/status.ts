/** 提交状态 → 徽章展示（状态字符串以后端实现为准：backend/app/api/v1/judge.py TERMINAL_STATUS） */
export type TagType = 'info' | 'primary' | 'success' | 'warning' | 'danger'

export interface StatusMeta {
  label: string
  type: TagType
}

const STATUS_META: Record<string, StatusMeta> = {
  pending: { label: '排队中', type: 'info' },
  compiling: { label: '编译中', type: 'primary' },
  running: { label: '运行中', type: 'primary' },
  accepted: { label: '通过 AC', type: 'success' },
  wrong_answer: { label: '答案错误 WA', type: 'danger' },
  compile_error: { label: '编译错误 CE', type: 'warning' },
  time_limit_exceeded: { label: '超时 TLE', type: 'warning' },
  memory_limit_exceeded: { label: '内存超限 MLE', type: 'warning' },
  output_limit_exceeded: { label: '输出超限 OLE', type: 'warning' },
  runtime_error: { label: '运行错误 RE', type: 'danger' },
  system_error: { label: '系统错误', type: 'danger' },
  judge_error: { label: '评测错误', type: 'danger' },
}

export function statusMeta(status: string): StatusMeta {
  return STATUS_META[status] || { label: status, type: 'info' }
}

export const ACTIVE_STATUSES = ['pending', 'compiling', 'running']
