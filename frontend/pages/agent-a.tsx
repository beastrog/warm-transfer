import { useEffect, useState } from 'react';
import { createRoom, transfer } from '../utils/api';
import { Room, createLocalAudioTrack, connect } from 'livekit-client';

export default function AgentA() {
  const [identity, setIdentity] = useState<string>('agent-a');
  const [roomName, setRoomName] = useState<string>('');
  const [room, setRoom] = useState<Room | null>(null);
  const [status, setStatus] = useState<string>('Idle');
  const [notes, setNotes] = useState<string>('');
  const [toRoom, setToRoom] = useState<string>('');
  const [summary, setSummary] = useState<string>('');

  async function handleJoin() {
    setStatus('Requesting token...');
    const res = await createRoom({ identity, role: 'agent' });
    setRoomName(res.room_name);
    setStatus('Connecting...');
    const r = await connect(process.env.NEXT_PUBLIC_LIVEKIT_URL || '', res.token);
    setRoom(r);
    setStatus('Connected as Agent A');

    try {
      const mic = await createLocalAudioTrack();
      await r.localParticipant.publishTrack(mic);
    } catch (e) {}
  }

  async function handleTransfer() {
    if (!roomName || !room) return;
    setStatus('Transferring...');
    const result = await transfer({
      from_room: roomName,
      initiator_identity: identity,
      target_identity: 'agent-b',
      transcript: notes,
    });
    setToRoom(result.to_room);
    setSummary(result.summary);

    // Notify Caller in original room to move using caller_token
    try {
      const msg = new TextEncoder().encode(JSON.stringify({
        type: 'warm_transfer',
        to_room: result.to_room,
        caller_token: result.caller_token,
      }));
      await room.localParticipant.publishData(msg, { reliable: true });
    } catch (e) {}

    // Join the new room using initiator token
    const newRoom = await connect(process.env.NEXT_PUBLIC_LIVEKIT_URL || '', result.initiator_token);
    try { room.disconnect(); } catch {}
    setRoom(newRoom);
    setStatus('Joined new room with Agent B and Caller');
  }

  useEffect(() => {
    return () => { room?.disconnect(); };
  }, [room]);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto bg-white rounded shadow p-6 space-y-4">
        <h1 className="text-2xl font-semibold">Agent A</h1>
        <button onClick={handleJoin} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Join as Agent A</button>
        <div className="text-sm text-gray-700">Status: {status}</div>
        {roomName && <div className="text-sm">Room: <span className="font-mono">{roomName}</span></div>}

        <div className="space-y-2">
          <label className="block text-sm font-medium">Transcript Notes</label>
          <textarea value={notes} onChange={e => setNotes(e.target.value)} className="w-full border rounded p-2 h-32" placeholder="Type caller context..." />
        </div>

        <button onClick={handleTransfer} className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">Transfer to Agent B</button>

        {toRoom && (
          <div className="mt-4 border rounded p-3 bg-gray-50">
            <div className="text-sm">New Room: <span className="font-mono">{toRoom}</span></div>
            <div className="mt-2">
              <div className="text-sm font-semibold">Summary to Read:</div>
              <p className="text-sm whitespace-pre-wrap">{summary}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
