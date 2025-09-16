import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

const axiosInstance = axios.create({
  baseURL: API_BASE,
  withCredentials: false, // Since we're not using cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

export async function createRoom(payload: { room_name?: string; identity: string; role: string; }) {
  const { data } = await axiosInstance.post('/create-room', payload);
  return data as { room_name: string; token: string };
}

export async function joinToken(payload: { room_name: string; identity: string; }) {
  const { data } = await axiosInstance.post('/join-token', payload);
  return data as { token: string };
}

export interface LLMStatus {
  available: boolean;
  provider?: string;
  model?: string;
  error?: string;
  loading?: boolean;
}

export async function checkLLMStatus(): Promise<LLMStatus> {
  try {
    const response = await axiosInstance.get('/health');
    const health = response.data;
    
    if (health.status !== 'ok') {
      console.warn('Backend health check failed:', health);
      return { 
        available: false, 
        error: 'Backend service unavailable',
        provider: 'unknown',
        model: 'unknown'
      };
    }
    
    // Return the LLM status from the health check
    return {
      available: health.llm?.available || false,
      provider: health.llm?.provider || 'unknown',
      model: health.llm?.model || 'unknown',
      error: health.llm?.error
    };
    
  } catch (error: any) {
    console.error('Health check failed:', error);
    return { 
      available: false, 
      error: error.response?.data?.detail || 'Service unavailable',
      provider: 'unknown',
      model: 'unknown'
    };
  }
}

interface TransferResponse {
  to_room: string;
  initiator_token: string;
  target_token: string;
  caller_token: string;
  summary: string;
  llm_available: boolean;
}

export async function transfer(payload: { 
  from_room: string; 
  initiator_identity: string; 
  target_identity: string; 
  to_room?: string; 
  transcript?: string; 
}): Promise<TransferResponse> {
  try {
    // First check LLM status
    const llmStatus = await checkLLMStatus();
    
    if (!llmStatus.available) {
      console.warn('LLM is not available, using fallback transfer');
      // Continue with transfer but indicate LLM is not available
      const { data } = await axiosInstance.post('/transfer', {
        ...payload,
        use_fallback: true // Tell backend to use fallback summary
      });
      return { ...data, llm_available: false };
    }
    
    // LLM is available, proceed with normal transfer
    const { data } = await axiosInstance.post('/transfer', payload);
    return { ...data, llm_available: true };
    
  } catch (error: any) {
    console.error('Transfer request failed:', error.response?.data || error.message);
    
    // If the error is due to LLM, try with fallback
    if (error.response?.status === 503 || error.response?.data?.detail?.includes('LLM')) {
      console.warn('LLM error, retrying with fallback');
      const { data } = await axiosInstance.post('/transfer', {
        ...payload,
        use_fallback: true
      });
      return { ...data, llm_available: false };
    }
    
    throw error;
  }
}

export async function getSummary(roomName: string) {
  const { data } = await axiosInstance.get(`/room/${roomName}/summary`);
  return data as { summary: string; transcript: string };
}

export async function twilioTransfer(payload: { 
  from_room: string; 
  caller_identity: string; 
  phone_number: string;
  timeout_seconds?: number;
}) {
  const { data } = await axiosInstance.post('/twilio-transfer', payload);
  return data as { call_sid: string; to_number: string; status: string };
}