import { useEffect, useState, useCallback } from 'react';
import { createRoom } from '../utils/api';
import { Room, createLocalAudioTrack, RemoteParticipant } from 'livekit-client';
import { motion, AnimatePresence } from 'framer-motion';
import { Phone, PhoneOff, Loader2, User, AlertTriangle } from 'lucide-react';

import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/Badge';
import { useToast } from '../components/ui/Toast';


type CallStatus = 'idle' | 'connecting' | 'connected' | 'transferring' | 'error';

export default function CallerPage() {
  const [roomName, setRoomName] = useState<string>('shared-room');
  const [identity] = useState<string>('caller');
  const [status, setStatus] = useState<CallStatus>('idle');
  const [room, setRoom] = useState<Room | null>(null);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [agentName, setAgentName] = useState<string>('');
  const { toast } = useToast();

  const handleJoin = useCallback(async () => {
    try {
      setStatus('connecting');
      
      // Join the shared room
      const res = await createRoom({ 
        identity: 'caller', 
        role: 'caller', 
        room_name: 'shared-room' // Hardcoded to ensure consistency
      });
      // Room name is already set to 'shared-room'
      
      // Initialize room
      const newRoom = new Room({
        adaptiveStream: true,
        dynacast: true,
      });

      // Set up room event listeners
      newRoom
        .on('participantConnected', (participant) => {
          if (participant.identity !== identity) {
            setAgentName(participant.identity);
            toast({
              title: 'Agent Connected',
              description: `${participant.identity} has joined the call`,
              variant: 'success',
            });
          }
        })
        .on('participantDisconnected', (participant) => {
          if (participant.identity !== identity) {
            toast({
              title: 'Agent Left',
              description: `${participant.identity} has left the call`,
              variant: 'warning',
            });
            setAgentName('');
          }
        })
        .on('disconnected', () => {
          setStatus('idle');
          setRoom(null);
          setAgentName('');
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

      // Listen for warm transfer signals
      newRoom.on('dataReceived', async (data: Uint8Array) => {
        try {
          const text = new TextDecoder().decode(data);
          const msg = JSON.parse(text);
          
          if (msg?.type === 'warm_transfer' && msg.caller_token && msg.to_room) {
            setStatus('transferring');
            toast({
              title: 'Transferring Call',
              description: 'Connecting you to another agent...',
              variant: 'info',
            });

            // Disconnect from current room
            newRoom.disconnect();

            // Connect to new room
            const transferRoom = new Room();
            await transferRoom.connect(livekitUrl, msg.caller_token);
            
            // Publish audio to new room
            try {
              const audioTrack = await createLocalAudioTrack();
              await transferRoom.localParticipant.publishTrack(audioTrack);
            } catch (error) {
              console.error('Failed to publish audio track after transfer', error);
            }

            setRoom(transferRoom);
            setRoomName(msg.to_room);
            setStatus('connected');
            setAgentName('Agent B');

            toast({
              title: 'Transfer Complete',
              description: 'You are now connected to a new agent',
              variant: 'success',
            });
          }
        } catch (error) {
          console.error('Error processing transfer:', error);
        }
      });

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

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (room) {
        room.disconnect();
      }
    };
  }, [room]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-xl font-semibold text-gray-900">Call Center</h1>
          <div className="flex items-center space-x-4
          ">
            {room && (
              <div className="flex items-center">
                <StatusBadge status={status === 'connected' ? 'connected' : status === 'transferring' ? 'connecting' : 'idle'} />
                <span className="ml-2 text-sm text-gray-600">
                  {status === 'connected' ? 'In Call' : status === 'transferring' ? 'Transferring...' : 'Ready'}
                </span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-grow flex items-center justify-center p-4">
        <AnimatePresence mode="wait">
          {!room ? (
            <motion.div
              key="join-card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="w-full max-w-md"
            >
              <Card>
                <CardHeader>
                  <CardTitle className="text-2xl font-bold text-center">Join as Caller</CardTitle>
                  <p className="text-sm text-gray-500 text-center mt-2">
                    Start a new call with an available agent
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
                        <Loader2 className="mr-3 h-5 w-5 animate-spin" />
                        Connecting...
                      </>
                    ) : (
                      <>
                        <Phone className="mr-3 h-5 w-5" />
                        Start Call
                      </>
                    )}
                  </Button>
                </CardFooter>
              </Card>
            </motion.div>
          ) : (
            <motion.div
              key="call-card"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="w-full max-w-4xl"
            >
              <Card className="overflow-hidden">
                <div className="p-6">
                  <div className="flex justify-between items-start">
                    <div>
                      <h2 className="text-lg font-medium text-gray-900">Ongoing Call</h2>
                      <p className="text-sm text-gray-500 mt-1">
                        {agentName ? `Connected with ${agentName}` : 'Connecting to an agent...'}
                      </p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        Room: {roomName}
                      </span>
                    </div>
                  </div>

                  <div className="mt-6">
                    <div className="p-6 bg-gray-100 rounded-lg flex items-center justify-center">
                      <div className="flex flex-col items-center space-y-3">
                        <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-white" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" />
                          </svg>
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-medium text-gray-900">Audio Call</p>
                          <p className="text-sm text-gray-500">Connected</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 flex justify-center space-x-4">
                    <Button
                      variant={isMuted ? 'outline' : 'secondary'}
                      size="lg"
                      onClick={toggleMute}
                      className="!h-12 !px-6"
                    >
                      {isMuted ? (
                        <PhoneOff className="h-5 w-5 text-red-600 mr-3" />
                      ) : (
                        <Phone className="h-5 w-5 text-green-600 mr-3" />
                      )}
                      <span>{isMuted ? 'Unmute' : 'Mute'}</span>
                    </Button>
                  </div>

                  {status === 'transferring' && (
                    <div className="mt-4 p-3 bg-yellow-50 rounded-md flex items-start">
                      <AlertTriangle className="h-5 w-5 text-yellow-400 mt-0.5 mr-2 flex-shrink-0" />
                      <div>
                        <h4 className="text-sm font-medium text-yellow-800">Transfer in Progress</h4>
                        <p className="text-sm text-yellow-700">Please wait while we connect you to another agent...</p>
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
