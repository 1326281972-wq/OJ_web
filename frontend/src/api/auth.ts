import http from './http'

export interface UserInfo {
  id: number
  user_id: string
  role: string
  nickname: string
}

export interface LoginResult {
  access_token: string
  token_type: string
  user: UserInfo
}

/** POST /api/v1/auth/register（公开） */
export async function register(
  user_id: string,
  password: string,
  nickname: string,
  email?: string,
): Promise<UserInfo> {
  const { data } = await http.post('/auth/register', { user_id, password, nickname, email })
  return data.data
}

/** POST /api/v1/auth/login（公开） */
export async function login(user_id: string, password: string): Promise<LoginResult> {
  const { data } = await http.post('/auth/login', { user_id, password })
  return data.data
}
