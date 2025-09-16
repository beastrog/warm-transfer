import { useEffect, useState, useCallback, useRef } from 'react';
import { createRoom, transfer, twilioTransfer, checkLLMStatus, LLMStatus as LLMStatusType } from '../utils/api';
import { 
  Room, 
  RoomEvent, 
  RemoteParticipant, 
  RemoteTrack, 
  LocalTrack, 
  Track,
  RemoteTrackPublication,
  TrackPublication,
  createLocalAudioTrack
} from 'livekit-client';
import { motion, AnimatePresence } from 'framer-motion';
import { Phone, PhoneOff, User, Loader2, PhoneCall, UserPlus, Copy, Check, Info } from 'lucide-react';

import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { StatusBadge } from '../components/ui/Badge';
import { useToast } from '../components/ui/Toast';

// Type definitions
interface TransferRequest {
  room_name: string;
  identity: string;
  target_agent: string;
  transcript: string;
}

interface TransferResponse {
  room_name: string;
  token: string;
  summary: string;
}

interface TwilioTransferRequest {
  room_name: string;
  identity: string;
  phone_number: string;
  transcript: string;
}

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
  const [transferInProgress, setTransferInProgress] = useState<boolean>(false);
  const [transferStatusText, setTransferStatusText] = useState<string>('');
  const [transferSummary, setTransferSummary] = useState<string>('');
  const [targetAgent, setTargetAgent] = useState<string>('agent-b');
  interface LLMState {
    available: boolean;
    loading: boolean;
    provider: string;
    model: string;
    error?: string;
  }

  const [llmStatus, setLlmStatus] = useState<LLMState>({ 
    available: false, 
    loading: true,
    provider: 'unknown',
    model: 'unknown'
  });
  const { toast } = useToast();
  
  // Check LLM status on component mount
  useEffect(() => {
    const checkLLM = async () => {
      try {
        const status = await checkLLMStatus();
        const newStatus: LLMState = {
          available: status.available ?? false,
          provider: status.provider || 'unknown',
          model: status.model || 'unknown',
          error: status.error,
          loading: false
        };
        
        setLlmStatus(newStatus);
        
        if (!status.available) {
          toast({
            title: 'LLM Not Available',
            description: status.error || 'AI summarization will use fallback text',
            variant: 'warning',
            duration: 5000,
          });
        }
      } catch (error) {
        console.error('Failed to check LLM status:', error);
        const errorStatus: LLMState = {
          available: false,
          loading: false,
          error: 'Failed to check LLM status',
          provider: 'unknown',
          model: 'unknown'
        };
        setLlmStatus(errorStatus);
      }
    };
    
    checkLLM();
  }, [toast]);
  
  const connectToRoom = useCallback(async () => {
    const roomName = 'shared-room'; // Hardcoded room name
    console.log(`Agent A attempting to connect to room: ${roomName}`);
    
    try {
      setStatus('connecting');
      
      // 1. Get room token (this will join the existing room or create a new one)
      const response = await createRoom({ 
        room_name: roomName, 
        identity: 'agent-a',
        role: 'agent' 
      });
      
      if (!response || !response.token) {
        throw new Error('Invalid response from server');
      }

      // 2. Create a new room instance
      const newRoom = new Room({
        adaptiveStream: true,
        audioCaptureDefaults: {
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true,
        },
        publishDefaults: {
          audioPreset: {
            maxBitrate: 16000
          }
        }
      });

      // 3. Set up room event listeners
      newRoom
        .on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
          console.log('Participant connected:', participant.identity);
          setCallerName(participant.identity);
          
          // Handle track subscriptions
          participant.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => {
            console.log('Track subscribed:', track.kind, 'from', participant.identity);
            if (track.kind === Track.Kind.Audio) {
              const audioElement = track.attach();
              document.body.appendChild(audioElement);
            }
          });
        })
        .on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
          console.log('Participant disconnected:', participant.identity);
          setCallerName('');
        })
        .on(RoomEvent.Disconnected, () => {
          console.log('Disconnected from room');
          setStatus('idle');
          setRoom(null);
          setCallerName('');
        });

      // 4. Connect to the room
      const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL;
      if (!livekitUrl) {
        throw new Error('LiveKit URL not configured');
      }

      console.log(`Agent A connecting to room: ${roomName}`);
      await newRoom.connect(livekitUrl, response.token);
      setRoom(newRoom);
      setStatus('connected');

      // 5. Publish local audio track
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

  const handleJoin = useCallback(async () => {
    if (status === 'connected') {
      toast({
        title: 'Already Connected',
        description: 'You are already in a call',
        variant: 'info',
      });
      return;
    }
    
    setStatus('connecting');
    setRoomName('shared-room'); // Ensure roomName is set
    
    try {
      await connectToRoom();
      setStatus('connected');
      
      toast({
        title: 'Call Connected',
        description: 'You have successfully joined the call',
        variant: 'success',
        duration: 2000,
      });
      
    } catch (error) {
      console.error('Failed to join room:', error);
      setStatus('error');
      setRoom(null);
      
      let errorMessage = 'Failed to connect to room';
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      }
      
      toast({
        title: 'Connection Error',
        description: errorMessage,
        variant: 'error',
      });
    }
  }, [status, connectToRoom, toast]);

  // Handle warm transfer to another agent
  const handleCompleteTransfer = useCallback(async () => {
    if (!room) return;
    
    try {
      setTransferInProgress(true);
      setTransferStatusText('Completing transfer...');
      
      // Force a state update to ensure UI reflects the transfer in progress
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Mute before transferring to avoid audio issues
      await toggleMute();
      
      // Notify other participants that the transfer is being completed
      try {
        const msg = new TextEncoder().encode(JSON.stringify({
          type: 'complete_transfer',
          target_agent: targetAgent,
          summary: transferSummary
        }));
        await room.localParticipant.publishData(msg, { reliable: true });
      } catch (e) {
        console.error('Failed to send transfer completion notification:', e);
      }
      
      // Update UI to show transfer is complete
      setTransferStatus('completed');
      setTransferInProgress(false);
      
      toast({
        title: 'Transfer Completed',
        description: `${targetAgent} has joined the call`,
        variant: 'success',
      });
      
      // Reset transfer status after a delay
      setTimeout(() => {
        setTransferStatus('idle');
        setTransferStatusText('');
      }, 3000);
      
    } catch (error) {
      console.error('Error completing transfer:', error);
      setTransferInProgress(false);
      toast({
        title: 'Transfer Failed',
        description: 'Could not complete the transfer. Please try again.',
        variant: 'error',
      });
    }
  }, [room, targetAgent, transferSummary, toast]);

  // Check LLM status when component mounts
  useEffect(() => {
    const checkLlm = async () => {
      try {
        const status = await checkLLMStatus();
        const llmState: LLMState = {
          ...status,
          loading: false,
          provider: status.provider || 'unknown',
          model: status.model || 'unknown',
        };
        
        setLlmStatus(llmState);
        
        if (!status.available) {
          console.warn('LLM not available:', status.error);
          toast({
            title: 'LLM Service Notice',
            description: `Using fallback mode: ${status.error || 'LLM service not available'}`,
            variant: 'warning',
            duration: 5000,
          });
        }
      } catch (error) {
        console.error('Failed to check LLM status:', error);
        const errorState: LLMState = {
          available: false,
          loading: false,
          error: 'Failed to check LLM status',
          provider: 'unknown',
          model: 'unknown'
        };
        setLlmStatus(errorState);
      }
    };
    
    checkLlm();
  }, [toast]);

  const handleWarmTransfer = useCallback(async () => {
    // Ensure we have an active room connection
    if (!room) {
      toast({
        title: 'No Active Call',
        description: 'Please join the call before initiating a transfer',
        variant: 'error',
      });
      return;
    }
    
    // Show LLM status if available
    if (llmStatus.loading) {
      toast({
        title: 'Checking AI Status',
        description: 'Please wait while we check the AI service status...',
        variant: 'info',
        duration: 2000,
      });
      return;
    }
    
    if (!llmStatus.available) {
      toast({
        title: 'AI Summarization Not Available',
        description: 'Proceeding with basic transfer. Some features may be limited.',
        variant: 'warning',
        duration: 3000,
      });
    }
    
    // Ensure roomName is set
    const currentRoomName = roomName || 'shared-room';
    if (!roomName) {
      setRoomName(currentRoomName);
    }
    
    // Prevent multiple transfers
    if (transferInProgress) {
      toast({
        title: 'Transfer in Progress',
        description: 'Please wait for the current transfer to complete',
        variant: 'warning',
      });
      return;
    }
    
    setTransferInProgress(true);
    setTransferStatusText('Preparing transfer...');
    
    try {
      // 1. Prepare transfer data
      const callTranscript = notes || 'No call notes available.';
      
      // 2. Show LLM status if available
      if (llmStatus.loading) {
        toast({
          title: 'Checking AI Status',
          description: 'Please wait while we check the AI service status...',
          variant: 'info',
          duration: 2000,
        });
      } else if (llmStatus.available && llmStatus.provider && llmStatus.model) {
        toast({
          title: 'AI Summary Available',
          description: `Using ${llmStatus.provider} (${llmStatus.model}) for transfer summary`,
          variant: 'success',
          duration: 3000,
        });
      } else {
        toast({
          title: 'AI Summarization Not Available',
          description: 'Proceeding with basic transfer. Some features may be limited.',
          variant: 'warning',
          duration: 3000,
        });
      }
      
      // 3. Initiate transfer with backend
      setTransferStatusText('Connecting to transfer service...');
      
      const result = await transfer({
        from_room: roomName,
        initiator_identity: identity,
        target_identity: targetAgent,
        transcript: callTranscript,
      }).catch(async (error) => {
        let errorMsg = 'Failed to initiate transfer';
        
        if (error.response?.status === 409) {
          errorMsg = 'A transfer is already in progress for this room';
        } else if (error.response?.data?.detail) {
          errorMsg = error.response.data.detail;
        } else if (error.message) {
          errorMsg = error.message;
        }
        
        throw new Error(errorMsg);
      });
      
      // 4. Update UI with transfer details
      setToRoom(result.to_room);
      setSummary(result.summary);
      setTransferSummary(result.summary);
      setTransferStatus('in_progress');
      
      // 5. Notify the caller about the transfer
      try {
        const transferData = {
          type: 'warm_transfer',
          to_room: result.to_room,
          caller_token: result.caller_token,
          summary: result.summary,
          llm_available: result.llm_available,
        };
        
        await room.localParticipant.publishData(
          new TextEncoder().encode(JSON.stringify(transferData)),
          { reliable: true }
        );
        
        // 6. Speak transfer notification to the caller
        if ('speechSynthesis' in window && result.summary) {
          try {
            const utterance = new SpeechSynthesisUtterance(
              `Transferring you to ${targetAgent}. Here's a summary: ${result.summary}`
            );
            window.speechSynthesis.speak(utterance);
          } catch (e) {
            console.warn('Could not speak summary:', e);
          }
        }
        
        // 7. Update transfer status
        const transferMessage = `Ask ${targetAgent} to join room: ${result.to_room}`;
        setTransferStatusText(transferMessage);
        
        toast({
          title: 'Transfer Initiated',
          description: transferMessage,
          variant: 'success',
        });
        
      } catch (error) {
        console.error('Failed to send transfer notification:', error);
        if (error.response?.data?.detail) {
          toast({
            title: 'Transfer Failed',
            description: error.response.data.detail,
            variant: 'error',
          });
        } else if (error instanceof Error) {
          toast({
            title: 'Transfer Failed',
            description: error.message || 'Failed to initiate transfer',
            variant: 'error',
          });
        } else {
          toast({
            title: 'Transfer Failed',
            description: 'An unknown error occurred during transfer',
            variant: 'error',
          });
        }
        setTransferStatus('error');
        setTransferStatusText('Transfer failed: ' + (error.message || 'Unknown error'));
      } finally {
        setTransferInProgress(false);
      }
      
    } catch (error) {
      console.error('Transfer failed:', error);
      
      toast({
        title: 'Transfer Failed',
        description: error.message || 'Could not complete the transfer',
        variant: 'error',
      });
      
      setTransferStatus('error');
      setTransferStatusText('Transfer failed: ' + (error.message || 'Unknown error'));
    } finally {
      setTransferInProgress(false);
    }
  }, [
    room, 
    roomName, 
    notes, 
    identity, 
    toast, 
    targetAgent, 
    transferInProgress, 
    setRoomName,
    setTransferInProgress,
    setTransferStatus,
    setTransferStatusText,
    setToRoom,
    setSummary,
    setTransferSummary
  ]);

  // Handle phone transfer
  const handlePhoneTransfer = useCallback(async () => {
    if (!roomName || !phone) {
      toast({
        title: 'Invalid Input',
        description: 'Please enter a valid phone number',
        variant: 'warning',
      });
      return;
    }
    
    if (transferInProgress) {
      toast({
        title: 'Transfer in Progress',
        description: 'Please wait for the current transfer to complete',
        variant: 'warning',
      });
      return;
    }
    
    setTransferInProgress(true);
    setTransferStatusText(`Transferring to ${phone}...`);
    
    try {
      const result = await twilioTransfer({
        from_room: roomName,
        caller_identity: identity,
        phone_number: phone,
        timeout_seconds: 30, // 30 seconds timeout for the call
      });
      
      setTransferStatusText('Connecting call...');
      
      // Update UI with transfer details
      toast({
        title: 'Transfer Initiated',
        description: `Connecting to ${phone}`,
        variant: 'success',
      });
      
      // Reset transfer status after a delay
      setTimeout(() => {
        setTransferInProgress(false);
        setTransferStatusText('');
      }, 3000);
      
    } catch (error) {
      console.error('Phone transfer failed:', error);
      setTransferInProgress(false);
      setTransferStatusText('Transfer failed');
      toast({
        title: 'Transfer Failed',
        description: error.message || 'Could not complete the phone transfer',
        variant: 'error',
      });
    }
  }, [roomName, phone, notes, identity, toast, transferInProgress]);

  // Toggle mute state
  const toggleMute = useCallback(async () => {
    if (!room) {
      toast({
        title: 'No Active Call',
        description: 'Please join a call first',
        variant: 'error',
      });
      return;
    }
    
    try {
      if (isMuted) {
        // Unmute by creating and publishing a new audio track
        const audioTrack = await createLocalAudioTrack();
        await room.localParticipant.publishTrack(audioTrack);
        setIsMuted(false);
        toast({
          title: 'Microphone Unmuted',
          variant: 'success',
          duration: 2000,
        });
      } else {
        // Mute by getting all audio track publications
        try {
          const publications = Array.from(room.localParticipant.audioTrackPublications.values());
          for (const publication of publications) {
            try {
              if (publication.track) {
                await room.localParticipant.unpublishTrack(publication.track);
                // Add a small delay to allow the track to be properly unpublished
                await new Promise(resolve => setTimeout(resolve, 100));
                if (publication.track) {
                  publication.track.stop();
                }
              }
            } catch (trackError) {
              console.warn('Error handling track:', trackError);
              // Continue with other tracks even if one fails
            }
          }
          
          setIsMuted(true);
          toast({
            title: 'Microphone Muted',
            variant: 'info' as const,
            duration: 2000,
          });
        } catch (error) {
          console.error('Error muting microphone:', error);
          throw error; // Re-throw to be caught by the outer catch
        }
      }
    } catch (error) {
      console.error('Error toggling mute:', error);
      let errorMessage = 'Could not toggle microphone';
      
      if (error instanceof Error) {
        errorMessage += `: ${error.message}`;
      }
      
      // Update the mute state to reflect the actual state
      const isActuallyMuted = !room?.localParticipant.audioTrackPublications.size;
      if (isActuallyMuted !== isMuted) {
        setIsMuted(isActuallyMuted);
      }
      
      toast({
        title: 'Microphone Error',
        description: errorMessage,
        variant: 'error',
        duration: 3000,
      });
    }
  }, [room, isMuted, toast, setIsMuted]);

  return (
    <div className="min-h-screen bg-gray-100">
            
      <div className="max-w-4xl mx-auto p-4">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Agent Console</h1>
          <div className="flex items-center space-x-2">
            <StatusBadge status={status} />
            {status === 'connected' && (
              <span className="text-sm text-gray-600">
                {callerName ? `Connected with ${callerName}` : 'Waiting for caller...'}
              </span>
            )}
          </div>
        </div>

        {transferInProgress && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-center">
            <Loader2 className="h-5 w-5 text-blue-500 animate-spin mr-3" />
            <span className="text-blue-700 font-medium">{transferStatusText}</span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Transfer Status Card - Shows when transfer is in progress */}
          {transferStatus === 'in_progress' && (
            <div className="col-span-3 mb-6">
              <Card>
                <CardHeader className="bg-blue-50 border-b border-blue-100">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <Loader2 className="h-5 w-5 text-blue-500 animate-spin mr-2" />
                      <CardTitle className="text-blue-700">Warm Transfer in Progress</CardTitle>
                    </div>
                    <span className="text-sm bg-blue-100 text-blue-800 px-3 py-1 rounded-full">
                      Step 1 of 2
                    </span>
                  </div>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="space-y-6">
                    {/* Progress Steps */}
                    <div className="relative">
                      <div className="flex items-center justify-between">
                        <div className="flex flex-col items-center space-y-1">
                          <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center">
                            <Check className="h-4 w-4" />
                          </div>
                          <span className="text-xs font-medium text-gray-700">Transfer Initiated</span>
                        </div>
                        <div className="h-1 flex-1 bg-blue-200 mx-2">
                          <div className="h-1 bg-blue-600 w-1/2"></div>
                        </div>
                        <div className="flex flex-col items-center space-y-1">
                          <div className="w-8 h-8 rounded-full border-2 border-blue-600 bg-white text-blue-600 flex items-center justify-center">
                            <span className="text-sm font-medium">2</span>
                          </div>
                          <span className="text-xs font-medium text-gray-500">Complete Transfer</span>
                        </div>
                      </div>
                    </div>

                    {/* Room Information */}
                    <div className="p-4 bg-blue-50 rounded-md border border-blue-100">
                      <h3 className="font-medium text-blue-800 mb-3">Agent B Join Information</h3>
                      <div className="space-y-3">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-sm text-gray-700 w-20">Room:</span>
                          <span className="font-mono bg-blue-100 px-3 py-1 rounded text-sm flex-1">
                            {toRoom}
                          </span>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(toRoom);
                              setCopied(true);
                              setTimeout(() => setCopied(false), 2000);
                            }}
                            className="text-blue-600 hover:text-blue-800 p-1 rounded hover:bg-blue-100"
                            title="Copy to clipboard"
                          >
                            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                          </button>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-sm text-gray-700 w-20">Agent:</span>
                          <span className="text-sm text-gray-800">{targetAgent}</span>
                        </div>
                      </div>
                      <p className="mt-3 text-sm text-blue-700 bg-blue-50 p-2 rounded">
                        Please provide the room name to <strong>{targetAgent}</strong> and wait for them to join before completing the transfer.
                      </p>
                    </div>

                    {/* Call Summary */}
                    {summary && (
                      <div className="p-4 bg-green-50 rounded-md border border-green-100">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="font-medium text-green-800">Call Summary</h3>
                          <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
                            Will be shared with {targetAgent}
                          </span>
                        </div>
                        <div className="bg-white p-3 rounded border border-green-100">
                          <p className="text-sm text-gray-700 whitespace-pre-line">{summary}</p>
                        </div>
                      </div>
                    )}

                    {/* Transfer Actions */}
                    <div className="flex justify-end space-x-3 pt-2">
                      <Button
                        variant="outline"
                        onClick={() => {
                          setTransferStatus('idle');
                          setTransferInProgress(false);
                          setTransferStatusText('');
                        }}
                        disabled={transferInProgress}
                      >
                        Cancel Transfer
                      </Button>
                      <Button
                        onClick={handleCompleteTransfer}
                        disabled={transferInProgress}
                        className="bg-blue-600 hover:bg-blue-700"
                      >
                        {transferInProgress ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Completing...
                          </>
                        ) : (
                          'Complete Transfer'
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Call Controls */}
          <Card className="col-span-1">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Call Controls</CardTitle>
                {status === 'connected' && (
                  <Button
                    onClick={toggleMute}
                    variant={isMuted ? 'outline' : 'secondary'}
                    size="sm"
                    className="h-8"
                  >
                    {isMuted ? 'Unmute' : 'Mute'}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Button
                  onClick={handleJoin}
                  disabled={status === 'connecting' || status === 'connected'}
                  className="w-full"
                >
                  {status === 'connecting' ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Phone className="mr-2 h-4 w-4" />
                  )}
                  {status === 'connected' ? 'Connected' : 'Join Call'}
                </Button>

                {status === 'connected' && (
                  <Button
                    onClick={() => room?.disconnect()}
                    variant="danger"
                    className="w-full"
                    disabled={transferInProgress}
                  >
                    <PhoneOff className="mr-2 h-4 w-4" />
                    End Call
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Transfer Controls */}
          <Card className="col-span-1">
            <CardHeader>
              <CardTitle>Transfer Call</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Transfer to Agent
                </label>
                <div className="space-y-2">
                  <Input
                    placeholder="Agent ID"
                    value={targetAgent}
                    onChange={(e) => setTargetAgent(e.target.value)}
                    disabled={status !== 'connected' || transferInProgress}
                    className="mb-2"
                  />
                  <Button
                    onClick={handleWarmTransfer}
                    disabled={status !== 'connected' || transferInProgress}
                    className="w-full"
                  >
                    {transferInProgress ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <UserPlus className="h-4 w-4 mr-2" />
                    )}
                    {transferInProgress ? 'Transferring...' : 'Warm Transfer'}
                  </Button>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-200">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Transfer to Phone
                </label>
                <div className="space-y-2">
                  <Input
                    placeholder="+1234567890"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    disabled={status !== 'connected' || transferInProgress}
                  />
                  <Button
                    onClick={handlePhoneTransfer}
                    disabled={status !== 'connected' || !phone || transferInProgress}
                    variant="outline"
                    className="w-full"
                  >
                    {transferInProgress ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <PhoneCall className="h-4 w-4 mr-2" />
                    )}
                    {transferInProgress ? 'Calling...' : 'Call Phone'}
                  </Button>
                </div>
              </div>
              
              {transferSummary && (
                <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded-md">
                  <div className="flex items-start">
                    <Info className="h-4 w-4 text-blue-500 mt-0.5 mr-2 flex-shrink-0" />
                    <div>
                      <h4 className="text-sm font-medium text-blue-800 mb-1">Transfer Summary</h4>
                      <p className="text-sm text-blue-700">{transferSummary}</p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Call Notes */}
          <Card className="col-span-1">
            <CardHeader>
              <CardTitle>Call Notes</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="Take notes during the call..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="min-h-[200px]"
                disabled={status !== 'connected'}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
