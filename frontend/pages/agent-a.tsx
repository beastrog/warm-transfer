import { useEffect, useState, useCallback } from 'react';
import { createRoom, transfer, twilioTransfer } from '../utils/api';
import { Room, createLocalAudioTrack, RemoteParticipant } from 'livekit-client';
import { motion, AnimatePresence } from 'framer-motion';
import { Phone, PhoneOff, User, Loader2, PhoneCall, UserPlus, Copy, Check } from 'lucide-react';

import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { StatusBadge } from '../components/ui/Badge';
import { useToast } from '../components/ui/Toast';
import VideoGrid from '../components/VideoGrid';

type TransferStatus = 'idle' | 'preparing' | 'in_progress' | 'completed' | 'error';

export default function AgentA() {
  const [identity] = useState<string>('agent-a');
  const [roomName, setRoomName] = useState<string>('');
  const [room, setRoom] = useState<Room | null>(null);
  const [status, setStatus] = useState<'idle' | 'connecting' | 'connected' | 'error'>('idle');
  const [transferStatus, setTransferStatus] = useState<TransferStatus>('idle');
  const [notes, setNotes] = useState<string>('');
  const [phone, setPhone] = useState<string>('');
  const [toRoom, setToRoom] = useState<string>('');
  const [summary, setSummary] = useState<string>('');
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [callerName, setCallerName] = useState<string>('');
  const [copied, setCopied] = useState<boolean>(false);
  const { toast } = useToast();

  const handleJoin = useCallback(async () => {
    try {
      setStatus('connecting');
      
      // Create or join a room
      const res = await createRoom({ identity, role: 'agent', room_name: 'shared-room' });
      setRoomName(res.room_name);
      
      // Initialize room
      const newRoom = new Room({
        adaptiveStream: true,
        dynacast: true,
      });

      // Set up room event listeners
      newRoom
        .on('participantConnected', (participant) => {
          if (participant.identity !== identity) {
            setCallerName(participant.identity);
            toast({
              title: 'Caller Connected',
              description: `${participant.identity} has joined the call`,
              variant: 'success',
            });
          }
        })
        .on('participantDisconnected', (participant) => {
          if (participant.identity !== identity) {
            toast({
              title: 'Caller Left',
              description: `${participant.identity} has left the call`,
              variant: 'warning',
            });
            setCallerName('');
          }
        })
        .on('disconnected', () => {
          setStatus('idle');
          setRoom(null);
          setCallerName('');
        });

      // Connect to the room
      const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL;
      if (!livekitUrl) {
        throw new Error('LiveKit URL not configured');
      }

      await newRoom.connect(livekitUrl, res.token);
      setRoom(newRoom);
      setStatus('connected');

      // Publish local audio track
      try {
        const audioTrack = await createLocalAudioTrack();
        await newRoom.localParticipant.publishTrack(audioTrack);
      } catch (error) {
        console.error('Failed to publish audio track', error);
        toast({
          title: 'Microphone Access',
          description: 'Could not access your microphone. Please check your permissions.',
          variant: 'error',
        });
      }
    } catch (error) {
      console.error('Error joining room:', error);
      setStatus('error');
      toast({
        title: 'Connection Failed',
        description: 'Could not connect to the call. Please try again.',
        variant: 'error',
      });
    }
  }, [identity, toast]);

  const handleTransfer = useCallback(async () => {
    if (!roomName || !room) return;
    
    try {
      setTransferStatus('preparing');
      
      // Initiate the transfer
      const result = await transfer({
        from_room: roomName,
        initiator_identity: identity,
        target_identity: 'agent-b',
        transcript: notes,
      });
      
      setToRoom(result.to_room);
      setSummary(result.summary);
      setTransferStatus('in_progress');

      // Notify the caller about the transfer
      try {
        const msg = new TextEncoder().encode(JSON.stringify({
          type: 'warm_transfer',
          to_room: result.to_room,
          caller_token: result.caller_token,
        }));
        await room.localParticipant.publishData(msg, { reliable: true });
      } catch (e) {
        console.error('Failed to send transfer notification:', e);
      }

      // Connect to the new room
      const newRoom = new Room();
      const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL;
      if (!livekitUrl) {
        throw new Error('LiveKit URL not configured');
      }

      await newRoom.connect(livekitUrl, result.initiator_token);
      
      // Set up the new room
      newRoom.on('participantConnected', (participant) => {
        if (participant.identity !== identity) {
          setCallerName(participant.identity);
        }
      });

      // Publish audio to the new room
      try {
        const audioTrack = await createLocalAudioTrack();
        await newRoom.localParticipant.publishTrack(audioTrack);
      } catch (error) {
        console.error('Failed to publish audio track after transfer', error);
      }

      // Clean up the old room
      room.disconnect();
      setRoom(newRoom);
      setStatus('connected');
      setTransferStatus('completed');

      toast({
        title: 'Transfer Complete',
        description: 'You are now in a conference with Agent B and the caller',
        variant: 'success',
      });

    } catch (error) {
      console.error('Transfer failed:', error);
      setTransferStatus('error');
      toast({
        title: 'Transfer Failed',
        description: 'Could not complete the transfer. Please try again.',
        variant: 'error',
      });
    }
  }, [room, roomName, identity, notes, toast]);

  const handleTransferToPhone = useCallback(async () => {
    if (!roomName || !phone) {
      toast({
        title: 'Phone Number Required',
        description: 'Please enter a valid phone number',
        variant: 'warning',
      });
      return;
    }

    try {
      setTransferStatus('in_progress');
      
      const resp = await twilioTransfer({ 
        from_room: roomName, 
        initiator_identity: identity, 
        phone_number: phone 
      });
      
      toast({
        title: 'Call Initiated',
        description: `Calling ${resp.to_number}...`,
        variant: 'success',
      });
      
      setTransferStatus('completed');
      
      // Update status when the call is connected
      const checkStatus = setInterval(async () => {
        try {
          // Here you would typically check the call status from your backend
          // For now, we'll just show a message
          toast({
            title: 'Call in Progress',
            description: `Connected to ${resp.to_number}`,
            variant: 'info',
          });
          clearInterval(checkStatus);
        } catch (error) {
          console.error('Error checking call status:', error);
          clearInterval(checkStatus);
        }
      }, 1000);
      
      return () => clearInterval(checkStatus);
      
    } catch (error) {
      console.error('Phone transfer failed:', error);
      setTransferStatus('error');
      toast({
        title: 'Call Failed',
        description: 'Could not initiate the phone call. Please try again.',
        variant: 'error',
      });
    }
  }, [roomName, phone, identity, toast]);

  // Toggle mute state
  const toggleMute = useCallback(async () => {
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
  }, [room, isMuted, toast]);

  // Copy room link to clipboard
  const copyRoomLink = useCallback(() => {
    if (!roomName) return;
    
    const url = `${window.location.origin}/caller?room=${encodeURIComponent(roomName)}`;
    navigator.clipboard.writeText(url);
    
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    
    toast({
      title: 'Link Copied',
      description: 'Caller link has been copied to clipboard',
      variant: 'success',
    });
  }, [roomName, toast]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (room) {
        room.disconnect();
      }
    };
  }, [room]);

  // Check for caller in the room
  useEffect(() => {
    if (room && status === 'connected') {
      const participants = Array.from(room.participants.values());
      const hasCallerParticipant = participants.some(p => p.identity !== identity);
      if (hasCallerParticipant) {
        setCallerName(participants.find(p => p.identity !== identity)?.identity || '');
      } else {
        setCallerName('');
      }
    }
  }, [room, status, identity]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-xl font-semibold text-gray-900">Call Center - Agent A</h1>
          <div className="flex items-center space-x-4">
            {room && (
              <div className="flex items-center">
                <StatusBadge status={status === 'connected' ? 'connected' : status === 'connecting' ? 'connecting' : 'idle'} />
                <span className="ml-2 text-sm text-gray-600">
                  {status === 'connected' ? 'In Call' : status === 'connecting' ? 'Connecting...' : 'Ready'}
                </span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-grow p-4">
        <AnimatePresence mode="wait">
          {!room ? (
            <motion.div
              key="join-card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="max-w-2xl mx-auto"
            >
              <Card>
                <CardHeader>
                  <CardTitle className="text-2xl font-bold text-center">Agent Dashboard</CardTitle>
                  <p className="text-sm text-gray-500 text-center mt-2">
                    Join as Agent A to start receiving calls
                  </p>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-center py-8">
                    <div className="w-24 h-24 rounded-full bg-blue-100 flex items-center justify-center">
                      <User className="w-10 h-10 text-blue-600" />
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="flex flex-col space-y-2">
                  <Button 
                    onClick={handleJoin} 
                    fullWidth 
                    size="lg"
                    disabled={status === 'connecting'}
                    className="relative overflow-hidden"
                  >
                    {status === 'connecting' ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Connecting...
                      </>
                    ) : (
                      <>
                        <Phone className="mr-2 h-4 w-4" />
                        Start Receiving Calls
                      </>
                    )}
                  </Button>
                </CardFooter>
              </Card>
            </motion.div>
          ) : (
            <div className="max-w-7xl mx-auto grid gap-6 md:grid-cols-3">
              {/* Left Column - Video and Controls */}
              <div className="md:col-span-2 space-y-6">
                <Card className="overflow-hidden">
                  <div className="p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h2 className="text-lg font-medium text-gray-900">
                          {callerName ? `Call with ${callerName}` : 'Waiting for caller...'}
                        </h2>
                        <p className="text-sm text-gray-500">
                          Room: <span className="font-mono">{roomName}</span>
                        </p>
                      </div>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={copyRoomLink}
                        className="flex items-center space-x-1"
                      >
                        {copied ? (
                          <>
                            <Check className="h-4 w-4" />
                            <span>Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-4 w-4" />
                            <span>Copy Link</span>
                          </>
                        )}
                      </Button>
                    </div>

                    <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden">
                      <VideoGrid room={room} />
                    </div>

                    <div className="mt-6 flex justify-center space-x-4">
                      <Button
                        variant={isMuted ? 'outline' : 'secondary'}
                        size="lg"
                        onClick={toggleMute}
                        className="rounded-full p-3"
                      >
                        {isMuted ? (
                          <PhoneOff className="h-5 w-5 text-red-600" />
                        ) : (
                          <Phone className="h-5 w-5 text-green-600" />
                        )}
                        <span className="ml-2">{isMuted ? 'Unmute' : 'Mute'}</span>
                      </Button>
                    </div>
                  </div>
                </Card>

                {/* Call Notes */}
                <Card>
                  <div className="p-6">
                    <h3 className="text-sm font-medium text-gray-900 mb-2">Call Notes</h3>
                    <Textarea 
                      value={notes} 
                      onChange={(e) => setNotes(e.target.value)} 
                      placeholder="Add notes about the call..."
                      className="min-h-[120px]"
                    />
                  </div>
                </Card>
              </div>

              {/* Right Column - Transfer Options */}
              <div className="space-y-6">
                {/* Transfer to Agent */}
                <Card>
                  <div className="p-6">
                    <div className="flex items-center space-x-2 mb-4">
                      <UserPlus className="h-5 w-5 text-blue-600" />
                      <h3 className="text-sm font-medium text-gray-900">Transfer to Agent B</h3>
                    </div>
                    <p className="text-sm text-gray-500 mb-4">
                      Initiate a warm transfer to another agent. Your notes will be shared automatically.
                    </p>
                    <Button 
                      onClick={handleTransfer} 
                      fullWidth
                      disabled={transferStatus === 'in_progress' || !callerName}
                      className="justify-center"
                    >
                      {transferStatus === 'in_progress' ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Transferring...
                        </>
                      ) : (
                        'Warm Transfer to Agent B'
                      )}
                    </Button>
                  </div>
                </Card>

                {/* Transfer to Phone */}
                <Card>
                  <div className="p-6">
                    <div className="flex items-center space-x-2 mb-4">
                      <PhoneCall className="h-5 w-5 text-green-600" />
                      <h3 className="text-sm font-medium text-gray-900">Transfer to Phone</h3>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <Input 
                          value={phone}
                          onChange={(e) => setPhone(e.target.value)}
                          placeholder="+1234567890"
                          className="w-full"
                        />
                        <p className="mt-1 text-xs text-gray-500">
                          Enter the phone number with country code
                        </p>
                      </div>
                      <Button 
                        onClick={handleTransferToPhone}
                        fullWidth
                        disabled={!phone || transferStatus === 'in_progress'}
                        className="justify-center"
                      >
                        {transferStatus === 'in_progress' ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Calling...
                          </>
                        ) : (
                          'Transfer to Phone'
                        )}
                      </Button>
                    </div>
                  </div>
                </Card>

                {/* Transfer Summary */}
                {transferStatus !== 'idle' && (
                  <Card>
                    <div className="p-6">
                      <h3 className="text-sm font-medium text-gray-900 mb-2">Transfer Status</h3>
                      {transferStatus === 'completed' && summary && (
                        <div className="space-y-3">
                          <div className="p-3 bg-green-50 rounded-md">
                            <p className="text-sm text-green-700">
                              Transfer successful! You are now in a conference with {toRoom.includes('agent-b') ? 'Agent B' : 'the phone number'}.
                            </p>
                          </div>
                          <div>
                            <h4 className="text-xs font-medium text-gray-500 mb-1">Summary Shared:</h4>
                            <p className="text-sm text-gray-700 whitespace-pre-wrap">{summary}</p>
                          </div>
                        </div>
                      )}
                      {transferStatus === 'in_progress' && (
                        <div className="p-3 bg-blue-50 rounded-md flex items-start">
                          <Loader2 className="h-4 w-4 text-blue-400 mt-0.5 mr-2 flex-shrink-0 animate-spin" />
                          <div>
                            <p className="text-sm text-blue-700">
                              Transfer in progress. Please wait...
                            </p>
                          </div>
                        </div>
                      )}
                      {transferStatus === 'error' && (
                        <div className="p-3 bg-red-50 rounded-md">
                          <p className="text-sm text-red-700">
                            Transfer failed. Please try again or contact support if the issue persists.
                          </p>
                        </div>
                      )}
                    </div>
                  </Card>
                )}
              </div>
            </div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
