import { useEffect, useState } from 'react';
import { joinToken, getSummary } from '../utils/api';
import { Room, createLocalAudioTrack, connect } from 'livekit-client';

export default function AgentB() {
  const [identity, setIdentity] = useState<string>('agent-b');
  const [roomName, setRoomName] = useState<string>('');
  const [room, setRoom] = useState<Room | null>(null);
  const [status, setStatus] = useState<string>('Idle');
  const [summary, setSummary] = useState<string>('');

  async function handleJoin() {
    if (!roomName) {
      alert('Enter room name (to_room) from transfer result.');
      return;
    }
    setStatus('Requesting token...');
    const tok = await joinToken({ room_name: roomName, identity });
    setStatus('Connecting...');
    const r = await connect(process.env.NEXT_PUBLIC_LIVEKIT_URL || '', tok.token);
    setRoom(r);
    setStatus('Connected as Agent B with context');

    try {
      const mic = await createLocalAudioTrack();
      await r.localParticipant.publishTrack(mic);
    } catch (e) {}

    const { summary } = await getSummary(roomName);
    setSummary(summary);
  }

  useEffect(() => {
    return () => { room?.disconnect(); };
  }, [room]);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto bg-white rounded shadow p-6 space-y-4">
        <h1 className="text-2xl font-semibold">Agent B</h1>
        <div className="space-y-2">
          <label className="block text-sm font-medium">Room Name (to_room)</label>
          <input value={roomName} onChange={e => setRoomName(e.target.value)} className="w-full border rounded p-2" placeholder="Enter room created during transfer" />
        </div>
        <button onClick={handleJoin} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Join as Agent B</button>
        <div className="text-sm text-gray-700">Status: {status}</div>
        {summary && (
          <div className="mt-4 border rounded p-3 bg-gray-50">
            <div className="text-sm font-semibold">Handoff Summary</div>
            <p className="text-sm whitespace-pre-wrap">{summary}</p>
          </div>
        )}
      </div>
    </div>
  );
}
