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

    useEffect(() => {
        return () => {
            if (audioPlayerRef.current) {
                URL.revokeObjectURL(audioPlayerRef.current.src);
            }
        };
    }, []);

    /*** Connection setup methods ***/
    const setupWebSocket = (): Promise<boolean> => {
        return new Promise((resolve) => {
            // Close any existing connection
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
                    if (data.transcript) {
                        setTranscript(prev => prev + " " + data.transcript);
                    }
                    if (data.audio) {
                        playAudioResponse(data.audio, data.contentType);
                    }
                } catch (e) {
                    console.error("Error parsing message:", e);
                }
            };
            
            socketRef.current = ws;
            
            // Set a timeout in case connection takes too long
            setTimeout(() => {
                if (ws.readyState !== WebSocket.OPEN) {
                    resolve(false);
                }
            }, 5000);
        });
    };

    /*** Play Audio on frontend setup ***/
    const playAudioResponse = (audioBase64: string, contentType: string) => {
    try {
        // Convert base64 to binary
        const audioBlob = base64ToBlob(audioBase64, contentType);
        
        // Create object URL from blob
        const audioUrl = URL.createObjectURL(audioBlob);
        
        // Create audio element if it doesn't exist yet
        if (!audioPlayerRef.current) {
            const audioElement = new Audio();
            audioElement.onended = () => {
                // Play next audio after the current one finishes
                console.log("Audio playback finished");
                URL.revokeObjectURL(audioElement.src); // Clean up
            };
            audioPlayerRef.current = audioElement;
        }
        
        // Set source and play audio
        audioPlayerRef.current.src = audioUrl;
        audioPlayerRef.current.play().catch(err => {
            console.error("Error playing audio:", err);
            setStatus("Error playing audio response");
        });
    } catch (err) {
        console.error("Error setting up audio playback:", err);
    }
};
    
      // Helper function to convert base64 to Blob
      const base64ToBlob = (base64: string, contentType: string): Blob => {
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
        
        return new Blob(byteArrays, { type: contentType });
      };

    /*** Make connection and recording methods ***/
    const startRecording = async () => {
        try {
            setIsLoading(true);
            
            // Step 1: Connect to WebSocket
            setStatus("Connecting to server...");
            const connected = await setupWebSocket();
            if (!connected) {
                setStatus("Failed to connect to server");
                setIsLoading(false);
                return;
            }
            
            // Step 2: Get microphone access
            setStatus("Requesting microphone access...");
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                streamRef.current = stream;
                
                // Step 3: Set up MediaRecorder
                const recorder = new MediaRecorder(stream, {
                    mimeType: 'audio/webm',
                });
                
                mediaRecorderRef.current = recorder;
                
                recorder.ondataavailable = async (event: BlobEvent) => {
                    if (socketRef.current && 
                        socketRef.current.readyState === WebSocket.OPEN && 
                        event.data.size > 0) {
                        // Convert Blob to ArrayBuffer before sending
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
                
                // Step 4: Start recording
                recorder.start(100); // Collect audio in small chunks (100ms)
                setIsRecording(true);
                
            } catch (error) {
                setStatus(`Microphone access error: ${error instanceof Error ? error.message : String(error)}`);
                console.error("Error accessing microphone:", error);
                // Close WebSocket if microphone access fails
                if (socketRef.current) {
                    socketRef.current.close();
                    socketRef.current = null;
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
        // Step 1: Stop the MediaRecorder
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
            mediaRecorderRef.current.stop();
        }
        
        // Step 2: Stop audio tracks
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        
        // Step 3: Close the WebSocket connection
        if (socketRef.current) {
            socketRef.current.close();
            socketRef.current = null;
        }
        
        setIsRecording(false);
        setStatus("Ready to record");
        setIsConnected("DISCONNECTED");
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