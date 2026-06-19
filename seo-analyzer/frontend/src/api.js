/**
 * API Client - Communicates with the FastAPI backend.
 * 
 * In development, Vite proxies /api/* to http://localhost:8000
 * In production, you'd set the baseURL to your deployed backend.
 */

import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000, // 2 minutes — audits can take a while
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Start a new SEO audit.
 * @param {string} url - The URL to analyze
 * @returns {Promise<object>} Complete audit results
 */
export async function runAudit(url) {
  const response = await api.post('/audit', { url })
  return response.data
}

/**
 * Get a previously completed audit by ID.
 * @param {number} id - Audit ID
 * @returns {Promise<object>} Audit results
 */
export async function getAudit(id) {
  const response = await api.get(`/audit/${id}`)
  return response.data
}

/**
 * List all past audits.
 * @param {number} limit - Max results to return
 * @param {number} offset - Pagination offset
 * @returns {Promise<object[]>} List of audit summaries
 */
export async function getHistory(limit = 50, offset = 0) {
  const response = await api.get('/history', { params: { limit, offset } })
  return response.data
}

/**
 * Get audit history for a specific URL (for drift comparison).
 * @param {string} url - URL to get history for
 * @returns {Promise<object[]>} List of audit summaries for that URL
 */
export async function getUrlHistory(url) {
  const response = await api.get('/history/url', { params: { url } })
  return response.data
}

/**
 * Run an AI visibility check.
 * @param {object} params - { query, target_url, provider, num_results }
 * @returns {Promise<object>} Visibility check results
 */
export async function checkVisibility({ query, target_url, provider, num_results }) {
  const response = await api.post('/visibility', { query, target_url, provider, num_results })
  return response.data
}

export default api
