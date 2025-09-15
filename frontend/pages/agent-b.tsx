import { useEffect, useState } from 'react';
import { joinToken, getSummary, transfer } from '../utils/api';
import { Room, createLocalAudioTrack } from 'livekit-client';
import Layout from '../components/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { useToast } from '../components/ui/Toast';

export default function AgentB() {
  const [identity, setIdentity] = useState<string>('agent-b');
  const [roomName, setRoomName] = useState<string>('');
  const [room, setRoom] = useState<Room | null>(null);
  const [status, setStatus] = useState<string>('Idle');
  const [summary, setSummary] = useState<string>('');
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const { toast } = useToast();

  async function handleJoin() {
    if (!roomName) {
      toast({
        title: 'Room Required',
        description: 'Enter room name (to_room) from transfer result.',
        variant: 'error',
      });
      return;
    }
    setStatus('Requesting token...');
    try {
      const tok = await joinToken({ room_name: roomName, identity });
      setStatus('Connecting...');
      const r = new Room();
      const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL;
      if (!livekitUrl) {
        console.error('NEXT_PUBLIC_LIVEKIT_URL is not set');
        setStatus('Error: LiveKit URL not configured');
        return;
      }
      try {
        await r.connect(livekitUrl, tok.token);
        setRoom(r);
        setStatus('Connected as Agent B with context');
        
        toast({
          title: 'Connected',
          description: 'You are now connected to the room',
          variant: 'success',
        });
      } catch (err) {
        console.error('Failed to connect to LiveKit', err);
        setStatus('Connection failed. Check LiveKit URL and token');
        try { r.disconnect(); } catch {}
        return;
      }

      try {
        const mic = await createLocalAudioTrack();
        await r.localParticipant.publishTrack(mic);
      } catch (e) {
        console.error('Failed to publish audio track', e);
      }

      const { summary } = await getSummary(roomName);
      setSummary(summary);
    } catch (error) {
      console.error('Error joining room:', error);
      setStatus('Failed to join room');
      toast({
        title: 'Join Failed',
        description: 'Could not join the room. Please check the room name and try again.',
        variant: 'error',
      });
    }
  }

  // Toggle mute state
  const toggleMute = async () => {
    if (!room || !room.localParticipant) return;

    try {
      if (isMuted) {
        const audioTrack = await createLocalAudioTrack();
        await room.localParticipant.publishTrack(audioTrack);
      } else {
        // Get all audio tracks from the local participant
        if (room.localParticipant.tracks) {
          const tracks = Array.from(room.localParticipant.tracks.values())
            .map(pub => pub.track)
            .filter((track): track is MediaStreamTrack => 
              track?.kind === 'audio' && track !== undefined
            );
          
          // Unpublish each audio track
          for (const track of tracks) {
            room.localParticipant.unpublishTrack(track);
            track.stop();
          }
        }
      }
      setIsMuted(!isMuted);
    } catch (error) {
      console.error('Error toggling mute:', error);
      toast({
        title: 'Microphone Error',
        description: 'Could not toggle mute. Please check your microphone permissions.',
        variant: 'error',
      });
    }
  };

  useEffect(() => {
    return () => { room?.disconnect(); };
  }, [room]);

  return (
    <Layout className="p-6">
      <div className="max-w-3xl mx-auto grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2 p-6 space-y-4">
          <h1 className="text-2xl font-semibold">Agent B</h1>
          <div className="space-y-2">
            <label className="block text-sm font-medium">Room Name (to_room)</label>
            <Input value={roomName} onChange={e => setRoomName(e.target.value)} placeholder="Enter room created during transfer" />
          </div>
          {!room ? (
            <Button onClick={handleJoin}>Join as Agent B</Button>
          ) : (
            <Button onClick={toggleMute}>
              {isMuted ? 'Unmute Microphone' : 'Mute Microphone'}
            </Button>
          )}
          <div className="text-sm text-gray-700">Status: {status}</div>
        </Card>
        <Card className="p-6 space-y-3">
          <div className="text-sm font-semibold">Handoff Summary</div>
          <p className="text-sm whitespace-pre-wrap">{summary}</p>
        </Card>
      </div>
    </Layout>
  );
}
