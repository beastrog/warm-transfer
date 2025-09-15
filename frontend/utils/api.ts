import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function createRoom(payload: { room_name?: string; identity: string; role: string; }) {
  const { data } = await axios.post(`${API_BASE}/create-room`, payload);
  return data as { room_name: string; token: string };
}

export async function joinToken(payload: { room_name: string; identity: string; }) {
  const { data } = await axios.post(`${API_BASE}/join-token`, payload);
  return data as { token: string };
}

export async function transfer(payload: { from_room: string; initiator_identity: string; target_identity: string; to_room?: string; transcript?: string; }) {
  const { data } = await axios.post(`${API_BASE}/transfer`, payload);
  return data as { to_room: string; initiator_token: string; target_token: string; caller_token: string; summary: string };
}

export async function getSummary(roomName: string) {
  const { data } = await axios.get(`${API_BASE}/room/${roomName}/summary`);
  return data as { summary: string; transcript: string };
}

export async function twilioTransfer(payload: { from_room: string; initiator_identity: string; phone_number: string; }) {
  const { data } = await axios.post(`${API_BASE}/twilio-transfer`, payload);
  return data as { call_sid: string; to_number: string; status: string };
}