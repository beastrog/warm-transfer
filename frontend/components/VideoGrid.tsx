import { useEffect, useRef, useState } from 'react';
import { 
  LocalTrackPublication, 
  RemoteTrackPublication, 
  Room, 
  Participant, 
  Track, 
  TrackPublication,
  LocalParticipant,
  RemoteParticipant,
  VideoTrack,
  RemoteVideoTrack,
  LocalVideoTrack
} from 'livekit-client';

interface VideoElement extends HTMLVideoElement {
  participantId?: string;
}

interface VideoElementWrapper {
  wrapper: HTMLDivElement;
  element: HTMLVideoElement;
}

const isLocalTrack = (
  pub: TrackPublication
): pub is LocalTrackPublication => {
  return pub.kind === Track.Kind.Video && pub.trackName !== undefined;
};

const isRemoteTrack = (
  pub: TrackPublication
): pub is RemoteTrackPublication => {
  return pub.kind === Track.Kind.Video && 'isSubscribed' in pub;
};

export default function VideoGrid({ room }: { room: Room | null }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [participantCount, setParticipantCount] = useState(1); // Start with 1 for local participant

  const getGridClass = (count: number) => {
    if (count <= 1) return 'grid-cols-1';
    if (count === 2) return 'grid-cols-1 md:grid-cols-2';
    return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3';
  };

  const updateParticipantCount = (room: Room | null) => {
    if (!room) {
      setParticipantCount(1);
      return;
    }
    try {
      const remoteParticipants = (room as any).remoteParticipants;
      const count = remoteParticipants?.size || 0;
      setParticipantCount(count + 1); // +1 for local participant
    } catch (e) {
      console.warn('Failed to update participant count:', e);
      setParticipantCount(1);
    }
  };

  useEffect(() => {
    if (!room || !containerRef.current) return;

    const container = containerRef.current;
    
    const createVideoElement = (
      pub: LocalTrackPublication | RemoteTrackPublication, 
      participant: Participant
    ): VideoElementWrapper | null => {
      const track = pub.track;
      if (!track || track.kind !== Track.Kind.Video) return null;
      
      const existing = container.querySelector(`[data-participant-id="${participant.identity}"]`) as VideoElement;
      if (existing) return null;

      // LiveKit track.attach() can return a single HTMLMediaElement or an array depending on version
      const attached = track.attach() as HTMLMediaElement | HTMLMediaElement[];
      const el = (Array.isArray(attached) ? attached[0] : attached) as HTMLVideoElement;
      const videoEl = el as VideoElement;
      videoEl.participantId = participant.identity;
      videoEl.setAttribute('data-participant-id', participant.identity);
      videoEl.className = 'w-full h-full object-cover rounded-xl bg-gray-900';
      
      const wrapper = document.createElement('div');
      wrapper.className = 'relative aspect-video rounded-xl overflow-hidden border border-gray-700';
      
      const nameTag = document.createElement('div');
      nameTag.className = 'absolute bottom-2 left-2 bg-black/70 text-white text-xs px-2 py-1 rounded';
      nameTag.textContent = participant.identity;
      
      wrapper.appendChild(videoEl);
      wrapper.appendChild(nameTag);
      
      return { wrapper, element: videoEl };
    };

    const attachPub = (
      pub: LocalTrackPublication | RemoteTrackPublication, 
      participant: Participant
    ) => {
      if (!pub.track || pub.kind !== Track.Kind.Video) return;
      
      const video = createVideoElement(pub, participant);
      if (video) {
        container.appendChild(video.wrapper);
      }
    };

    const detachPub = (
      pub: LocalTrackPublication | RemoteTrackPublication, 
      participant: Participant
    ) => {
      if (!pub.track) return;
      const element = container.querySelector(`[data-participant-id="${participant.identity}"]`);
      if (element && element.parentElement) {
        element.parentElement.remove();
      }
      // LiveKit track.detach() can return a single element or an array
      const detached = pub.track.detach() as Element | Element[] | undefined;
      if (Array.isArray(detached)) {
        detached.forEach(el => el && el.remove());
      } else if (detached instanceof Element) {
        detached.remove();
      }
    };

        // Handle local participant
    try {
      if (room.localParticipant) {
        const localParticipant = room.localParticipant as any;
        if (localParticipant?.tracks) {
          const videoTracks = Array.from(localParticipant.tracks.values())
            .filter((pub: any) => 
              pub?.kind === Track.Kind.Video && pub?.track !== undefined
            );
          
          videoTracks.forEach((pub: any) => {
            attachPub(pub, room.localParticipant);
          });
        }
      }
    } catch (e) {
      console.warn('Failed to handle local participant:', e);
    }
    
    // Handle remote participants
    // Event handlers
    const onParticipantConnected = (participant: RemoteParticipant) => {
      updateParticipantCount(room);
      try {
        const remoteParticipant = participant as any;
        if (remoteParticipant?.tracks) {
          const videoTracks = Array.from(remoteParticipant.tracks.values())
            .filter((pub: any) => 
              pub?.kind === Track.Kind.Video && pub?.track !== undefined
            );
          
          videoTracks.forEach((pub: any) => {
            attachPub(pub, participant);
          });
        }
      } catch (e) {
        console.warn('Failed to handle participant connected:', e);
      }
    };

    const onParticipantDisconnected = (participant: RemoteParticipant) => {
      updateParticipantCount(room);
      try {
        const remoteParticipant = participant as any;
        if (remoteParticipant?.tracks) {
          const videoTracks = Array.from(remoteParticipant.tracks.values())
            .filter((pub: any) => pub?.track !== undefined);
          
          videoTracks.forEach((pub: any) => {
            detachPub(pub, participant);
          });
        }
      } catch (e) {
        console.warn('Failed to handle participant disconnected:', e);
      }
    };

    const onTrackPublished = (
      pub: RemoteTrackPublication,
      participant: RemoteParticipant
    ) => {
      if (pub.kind === Track.Kind.Video) {
        attachPub(pub, participant);
      }
    };

    const onTrackUnpublished = (
      pub: RemoteTrackPublication,
      participant: RemoteParticipant
    ) => {
      if (pub.kind === Track.Kind.Video) {
        detachPub(pub, participant);
      }
    };

    // Attach existing participants using LiveKit v2 API
    try {
      const rp = (room as any).remoteParticipants;
      if (rp && typeof rp.forEach === 'function') {
        rp.forEach((participant: RemoteParticipant) => {
          try {
            const videoTracks = Array.from((participant as any).videoTracks?.values() || [])
              .filter((pub: any): pub is RemoteTrackPublication & { track: RemoteVideoTrack } => 
                pub?.track !== undefined
              );
            
            videoTracks.forEach(pub => {
              try {
                attachPub(pub, participant);
              } catch (e) {
                console.warn('Failed to attach publication:', e);
              }
            });
          } catch (e) {
            console.warn('Failed to process participant tracks:', e);
          }
        });
      }
    } catch (e) {
      console.warn('Failed to process remote participants:', e);
    }
    }
    updateParticipantCount(room);

    // Set up event listeners
    room
      .on('participantConnected', onParticipantConnected)
      .on('participantDisconnected', onParticipantDisconnected)
      .on('trackPublished', onTrackPublished)
      .on('trackUnpublished', onTrackUnpublished);

    return () => {
      try {
        if (room) {
          room
            .off('participantConnected', onParticipantConnected)
            .off('participantDisconnected', onParticipantDisconnected)
            .off('trackPublished', onTrackPublished)
            .off('trackUnpublished', onTrackUnpublished);
        }
        
        // Clean up all video elements
        const videos = containerRef.current?.querySelectorAll('video');
        videos?.forEach(el => {
          try {
            el.pause();
            el.srcObject = null;
          } catch (e) {
            console.warn('Failed to cleanup video element:', e);
          }
        });
        if (containerRef.current) {
          containerRef.current.innerHTML = '';
        }
      } catch (e) {
        console.warn('Failed to cleanup VideoGrid:', e);
      }
    };
  }, [room]);

  return (
    <div 
      ref={containerRef} 
      className={`grid ${getGridClass(participantCount)} gap-4 w-full`}
    />
  );
}
