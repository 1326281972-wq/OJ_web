import http from './http'

export interface SubmissionListItem {
  id: number
  problem_id: number
  language: string
  status: string
  time_used: number | null
  memory_used: number | null
  submitted_at: string | null
}

export interface SubmissionStatusItem {
  id: number
  status: string
}

export interface SubmissionDetail extends SubmissionListItem {
  code: string
  compile_info: string | null
  run_info: string | null
}

export interface SubmissionListResp {
  total: number
  items: SubmissionListItem[]
}

/** POST /api/v1/submissions（需登录） */
export async function createSubmission(
  problem_id: number,
  language: string,
  code: string,
): Promise<SubmissionListItem> {
  const { data } = await http.post('/submissions', { problem_id, language, code })
  return data.data
}

/** GET /api/v1/submissions（需登录，分页） */
export async function listSubmissions(page = 1, page_size = 20): Promise<SubmissionListResp> {
  const { data } = await http.get('/submissions', { params: { page, page_size } })
  return data.data
}

/** GET /api/v1/submissions/status?ids=（批量状态，轮询用） */
export async function getSubmissionStatus(ids: number[]): Promise<SubmissionStatusItem[]> {
  const { data } = await http.get('/submissions/status', { params: { ids: ids.join(',') } })
  return data.data
}

/** GET /api/v1/submissions/{id}（详情，本人或管理员） */
export async function getSubmission(id: number): Promise<SubmissionDetail> {
  const { data } = await http.get(`/submissions/${id}`)
  return data.data
}
