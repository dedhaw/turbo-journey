import { useState, useRef, useEffect } from "react"

export default function AudioCapture() {
    const [isRecording, setIsRecording] = useState<boolean>(false);
    const [isConnected, setIsConnected] = useState<string>("DISCONNECTED");
    const [status, setStatus] = useState<string>("Ready to record");
    const [transcript, setTranscript] = useState<string>("");
    const [isLoading, setIsLoading] = useState<boolean>(false);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const socketRef = useRef<WebSocket | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
    const audioQueueRef = useRef<Array<{blob: Blob, sentence: string}>>([]);
    const isPlayingRef = useRef<boolean>(false);
    const aiSpeakingRef = useRef<boolean>(false);
    const isRecordingRef = useRef<boolean>(false);

    useEffect(() => {
        isRecordingRef.current = isRecording;
    }, [isRecording]);

    useEffect(() => {
        return () => {
            if (audioPlayerRef.current) {
                audioPlayerRef.current.pause();
                URL.revokeObjectURL(audioPlayerRef.current.src);
            }
            stopRecording();
        };
    }, []);

    /*** Connection setup methods ***/
    const setupWebSocket = (): Promise<boolean> => {
        return new Promise((resolve) => {
            if (socketRef.current) {
                socketRef.current.close();
                socketRef.current = null;
            }
            
            setStatus("Connecting to server...");
            const ws = new WebSocket("ws://localhost:8000/listen");
            
            ws.onopen = () => {
                setStatus("Connected to server");
                setIsConnected("CONNECTED");
                console.log("WebSocket connected");
                resolve(true);
            };
            
            ws.onclose = () => {
                setStatus("Disconnected from server");
                setIsConnected("DISCONNECTED");
                console.log("WebSocket closed");
                resolve(false);
            };
            
            ws.onerror = (error) => {
                setStatus("Connection error");
                setIsConnected("ERROR");
                console.error("WebSocket error", error);
                resolve(false);
            };
            
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log("Received WebSocket message:", data);
                    
                    if (data.status) {
                        console.log(`Server status: ${data.status}`, data.message);
                        
                        if (data.status === "listening") {
                            setStatus("Listening to your voice...");
                        } else if (data.status === "stopped") {
                            setStatus("Listening stopped");
                            setIsConnected("DISCONNECTED");
                        } else if (data.status === "ready") {
                            setStatus("Server ready");
                        }
                    }
                    
                    if (data.transcript) {
                        console.log("Received transcript:", data.transcript);
                        setTranscript(data.transcript);
                        aiSpeakingRef.current = true;
                        console.log("AI started speaking - microphone input will be muted");
                        console.log("Set aiSpeakingRef to true");
                    }
                    
                    if (data.audio) {
                        console.log("Received audio data, sentence:", data.sentence);
                        console.log("Current recording state:", isRecordingRef.current); // Use ref instead
                        console.log("AI speaking state:", aiSpeakingRef.current);
                        
                        if (!isRecordingRef.current) {
                            console.log("Not recording anymore, ignoring audio");
                            return;
                        }
                        
                        if (!aiSpeakingRef.current) {
                            console.log("AI was interrupted, ignoring incoming audio");
                            return;
                        }
                        
                        const audioBlob = base64ToBlob(data.audio, data.content_type);
                        console.log("Created audio blob, size:", audioBlob.size, "type:", audioBlob.type);
                        audioQueueRef.current.push({ blob: audioBlob, sentence: data.sentence });
                        console.log("Audio queue length after push:", audioQueueRef.current.length);
                        
                        if (!isPlayingRef.current) {
                            console.log("Starting audio playback");
                            playNextAudio();
                        } else {
                            console.log("Audio already playing, added to queue");
                        }
                    }
                    
                    if (data.deepgram_status) {
                        console.log(`Deepgram connection ${data.deepgram_status}`);
                        if (data.deepgram_status === "closed") {
                            setStatus("AI speaking - microphone paused");
                        } else if (data.deepgram_status === "reopened") {
                            setStatus("Listening to your voice...");
                        } else if (data.deepgram_status === "failed_to_reopen") {
                            setStatus("Connection issue - please restart recording");
                            console.error("Failed to reopen Deepgram connection");
                        }
                    }
                    
                    if (data.interrupt) {
                        console.log("Interruption detected, stopping audio playback");
                        stopAudioPlayback();
                        aiSpeakingRef.current = false;
                        setStatus("Listening to your voice...");
                    }
                    
                    if (data.ai_finished_speaking) {
                        console.log("Backend says AI finished speaking");
                        if (audioQueueRef.current.length === 0 && !isPlayingRef.current) {
                            aiSpeakingRef.current = false;
                            console.log("Set aiSpeakingRef to false - backend confirmed all audio sent");
                        } else {
                            console.log("Audio still in queue or playing, keeping aiSpeakingRef true");
                        }
                    }
                    
                    if (data.error) {
                        console.error("Server error:", data.error);
                        setStatus(`Error: ${data.error}`);
                    }
                } catch (e) {
                    console.error("Error parsing message:", e);
                }
            };
            
            socketRef.current = ws;
            
            setTimeout(() => {
                if (ws.readyState !== WebSocket.OPEN) {
                    resolve(false);
                }
            }, 5000);
        });
    };

    /*** Play Audio on frontend setup ***/
    const playNextAudio = async () => {
        console.log("playNextAudio called, isRecordingRef:", isRecordingRef.current);
        console.log("Queue length:", audioQueueRef.current.length);
        console.log("isPlayingRef:", isPlayingRef.current);
        
        if (!isRecordingRef.current) {
            console.log("Recording stopped, canceling audio playback");
            isPlayingRef.current = false;
            return;
        }
        
        if (audioQueueRef.current.length === 0) {
            isPlayingRef.current = false;
            console.log("Audio queue is empty, finished playing");
            console.log("Queue empty, isPlayingRef set to false");
            return;
        }
        
        isPlayingRef.current = true;
        const nextAudio = audioQueueRef.current.shift()!;
        
        console.log("Playing next audio sentence:", nextAudio.sentence);
        console.log("Remaining queue length:", audioQueueRef.current.length);
        
        const audioUrl = URL.createObjectURL(nextAudio.blob);
        
        try {
            if (!audioPlayerRef.current) {
                console.log("Creating new audio element");
                const audioElement = new Audio();
                audioElement.preload = 'auto';
                audioElement.volume = 1.0;
                
                audioElement.onended = () => {
                    console.log("Audio ended, cleaning up and playing next");
                    URL.revokeObjectURL(audioElement.src);
                    playNextAudio(); 
                };
                
                audioElement.onerror = (e) => {
                    console.error("Audio element error:", e);
                    URL.revokeObjectURL(audioUrl);
                    isPlayingRef.current = false;
                    if (audioQueueRef.current.length > 0 && isRecordingRef.current) {
                        setTimeout(() => playNextAudio(), 100);
                    }
                };
                
                audioPlayerRef.current = audioElement;
            }
            
            if (!isRecordingRef.current) {
                console.log("Recording stopped during audio setup, aborting");
                URL.revokeObjectURL(audioUrl);
                isPlayingRef.current = false;
                return;
            }
            
            audioPlayerRef.current.src = audioUrl;
            console.log("About to play audio...");
            await audioPlayerRef.current.play();
            console.log("Audio playback started successfully");
            
        } catch (err) {
            console.error("Error playing audio:", err);
            setStatus(`Error playing audio response: ${err}`);
            isPlayingRef.current = false;
            URL.revokeObjectURL(audioUrl);
            
            if (audioQueueRef.current.length > 0 && isRecordingRef.current) {
                setTimeout(() => playNextAudio(), 100);
            }
        }
    };
    
    const stopAudioPlayback = () => {
        console.log("Force stopping all audio playback");
        
        if (audioPlayerRef.current) {
            audioPlayerRef.current.pause();
            audioPlayerRef.current.currentTime = 0;
            
            if (audioPlayerRef.current.src) {
                URL.revokeObjectURL(audioPlayerRef.current.src);
                audioPlayerRef.current.src = "";
            }
        }
        
        audioQueueRef.current.forEach(audio => {
            if (audio.blob) {
                try {
                    const blobUrl = URL.createObjectURL(audio.blob);
                    URL.revokeObjectURL(blobUrl);
                } catch (e) {
                    console.log("Error revoking blob URL:", e);
                }
            }
        });
        
        audioQueueRef.current = []; 
        isPlayingRef.current = false;
        aiSpeakingRef.current = false;
        
        console.log("Audio playback force stopped and queue cleared");
    };
    
    const base64ToBlob = (base64: string, contentType: string): Blob => {
        try {
            console.log("Converting base64 to blob, content type:", contentType);
            const byteCharacters = atob(base64);
            const byteArrays = [];
            
            for (let offset = 0; offset < byteCharacters.length; offset += 512) {
                const slice = byteCharacters.slice(offset, offset + 512);
                
                const byteNumbers = new Array(slice.length);
                for (let i = 0; i < slice.length; i++) {
                    byteNumbers[i] = slice.charCodeAt(i);
                }
                
                const byteArray = new Uint8Array(byteNumbers);
                byteArrays.push(byteArray);
            }
            
            const blob = new Blob(byteArrays, { type: contentType });
            console.log("Blob created successfully, size:", blob.size);
            return blob;
        } catch (error) {
            console.error("Error converting base64 to blob:", error);
            throw error;
        }
    };

    /*** Make connection and recording methods ***/
    const startRecording = async () => {
        try {
            setIsLoading(true);
            
            stopAudioPlayback();
            
            setStatus("Connecting to server...");
            const connected = await setupWebSocket();
            if (!connected) {
                setStatus("Failed to connect to server");
                setIsLoading(false);
                return;
            }
            
            socketRef.current!.send(JSON.stringify({
                action: "start_listening"
            }));
            
            setStatus("Requesting microphone access...");
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true,
                        sampleRate: 44100
                    }
                });
                streamRef.current = stream;
                
                const recorder = new MediaRecorder(stream, {
                    mimeType: 'audio/webm',
                });
                
                mediaRecorderRef.current = recorder;
                
                recorder.ondataavailable = async (event: BlobEvent) => {
                    if (socketRef.current && 
                        socketRef.current.readyState === WebSocket.OPEN && 
                        event.data.size > 0) {
                        
                        const arrayBuffer = await event.data.arrayBuffer();
                        socketRef.current.send(arrayBuffer);
                    }
                };
                
                recorder.onstart = () => {
                    setStatus("Recording...");
                };
                
                recorder.onerror = (event) => {
                    setStatus(`Recording error: ${event.error}`);
                };
                
                recorder.start(100);
                setIsRecording(true);
                
            } catch (error) {
                setStatus(`Microphone access error: ${error instanceof Error ? error.message : String(error)}`);
                console.error("Error accessing microphone:", error);
                
                if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
                    socketRef.current.send(JSON.stringify({
                        action: "stop_listening"
                    }));
                }
            }
            
        } catch (error) {
            setStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
            console.error("Error starting recording:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const stopRecording = () => {
        console.log("Stop recording clicked");
        
        stopAudioPlayback();
        
        setIsRecording(false);
        
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
            mediaRecorderRef.current.stop();
        }
        
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify({
                action: "stop_listening"
            }));
            
            setTimeout(() => {
                if (socketRef.current) {
                    console.log("Closing WebSocket connection");
                    socketRef.current.close();
                    socketRef.current = null;
                }
            }, 100);
        }
        
        setStatus("Ready to record");
        console.log("Stop recording completed");
    };

    return (
        <div>
            <h1>Audio Capture with Live Streaming</h1>
            <div className="status">Status: {status}</div>
            <div className="connection">Connection: {isConnected}</div>
            <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={isLoading}
            >
                {isLoading ? "Please wait..." : isRecording ? "Stop Recording" : "Start Recording"}
            </button>
            {transcript && (
                <div className="transcript">
                    <h3>Transcript:</h3>
                    <p>{transcript}</p>
                    <button onClick={() => setTranscript("")}>Clear</button>
                </div>
            )}
        </div>
    )
}