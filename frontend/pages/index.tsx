import { useEffect, useState } from 'react';
import { createRoom } from '../utils/api';
import { Room, createLocalAudioTrack, connect, DataPacket_Kind } from 'livekit-client';

export default function Home() {
  const [roomName, setRoomName] = useState<string>('');
  const [identity, setIdentity] = useState<string>('caller');
  const [status, setStatus] = useState<string>('Idle');
  const [room, setRoom] = useState<Room | null>(null);

  async function handleJoin() {
    setStatus('Requesting token...');
    const res = await createRoom({ identity, role: 'caller' });
    setRoomName(res.room_name);
    setStatus('Connecting...');
    const r = await connect(process.env.NEXT_PUBLIC_LIVEKIT_URL || '', res.token);
    setRoom(r);
    setStatus('Connected as Caller');

    try {
      const mic = await createLocalAudioTrack();
      await r.localParticipant.publishTrack(mic);
    } catch (e) {}

    // Listen for warm transfer signal
    r.on('dataReceived', async (payload) => {
      try {
        const text = new TextDecoder().decode(payload.data);
        const msg = JSON.parse(text);
        if (msg?.type === 'warm_transfer' && msg.caller_token && msg.to_room) {
          setStatus('Transferring to new room...');
          try { r.disconnect(); } catch {}
          const newRoom = await connect(process.env.NEXT_PUBLIC_LIVEKIT_URL || '', msg.caller_token);
          setRoom(newRoom);
          setRoomName(msg.to_room);
          setStatus('Connected in new room with Agent B');
          try {
            const mic2 = await createLocalAudioTrack();
            await newRoom.localParticipant.publishTrack(mic2);
          } catch (e) {}
        }
      } catch {}
    });
  }

  useEffect(() => {
    return () => {
      room?.disconnect();
    }
  }, [room]);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-xl mx-auto bg-white rounded shadow p-6 space-y-4">
        <h1 className="text-2xl font-semibold">Caller</h1>
        <p className="text-sm text-gray-600">Join a room and connect to LiveKit</p>
        <button onClick={handleJoin} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Join as Caller</button>
        <div className="text-sm text-gray-700">Status: {status}</div>
        {roomName && <div className="text-sm">Room: <span className="font-mono">{roomName}</span></div>}
      </div>
    </div>
  );
}
