import http from './http'

export interface ProblemListItem {
  id: number
  title: string
  time_limit: number
  memory_limit: number
  spj: number
}

export interface ProblemDetail extends ProblemListItem {
  description: string
  input: string
  output: string
  sample_input: string
  sample_output: string
  defunct: boolean
}

export interface ProblemListResp {
  total: number
  items: ProblemListItem[]
}

/** GET /api/v1/problems（需登录，分页） */
export async function listProblems(
  page = 1,
  page_size = 20,
  keyword?: string,
): Promise<ProblemListResp> {
  const { data } = await http.get('/problems', { params: { page, page_size, keyword } })
  return data.data
}

/** GET /api/v1/problems/{id}（需登录） */
export async function getProblem(id: number): Promise<ProblemDetail> {
  const { data } = await http.get(`/problems/${id}`)
  return data.data
}
