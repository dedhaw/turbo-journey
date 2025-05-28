import React, { useState, useEffect, useRef } from "react";

const AudioCapture: React.FC = () => {
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [status, setStatus] = useState<string>("Connecting...");
  const [transcript, setTranscript] = useState<string>("");
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  
  useEffect(() => {
    // Set up WebSocket connection to FastAPI backend
    setupWebSocket();
    
    requestMicrophoneAccess();
    
    return () => {
      cleanupResources();
    };
  }, []);
  
  const setupWebSocket = () => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      return;
    }
    
    const ws = new WebSocket("ws://localhost:8000/listen");
    
    ws.onopen = () => {
      setStatus("Connected to server");
      setIsConnected(true);
      console.log("WebSocket connected");
    };
    
    ws.onclose = () => {
      setStatus("Disconnected from server");
      setIsConnected(false);
      console.log("WebSocket closed");
      
      setTimeout(setupWebSocket, 2000);
    };
    
    ws.onerror = (error) => {
      setStatus("Connection error");
      setIsConnected(false);
      console.error("WebSocket error", error);
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.transcript) {
          setTranscript(prev => prev + " " + data.transcript);
        }
      } catch (e) {
        console.error("Error parsing message:", e);
      }
    };
    
    socketRef.current = ws;
  };
  
  const requestMicrophoneAccess = async () => {
    try {
      // Request microphone access upfront
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      
      // Stop tracks initially but keep the stream reference
      stream.getTracks().forEach(track => track.stop());
      
      setStatus("Ready to record");
    } catch (error) {
      setStatus(`Microphone access error: ${error instanceof Error ? error.message : String(error)}`);
      console.error("Error accessing microphone:", error);
    }
  };

  // Start recording and send audio to WebSocket
  const startRecording = async () => {
    try {
      // Make sure WebSocket is connected
      if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
        setupWebSocket();
        await new Promise(resolve => setTimeout(resolve, 500)); // Give time to connect
      }
      
      setStatus("Requesting microphone access...");
      
      // Reuse stream if possible, otherwise get a new one
      let stream;
      if (!streamRef.current || streamRef.current.getTracks().length === 0 || 
          streamRef.current.getTracks()[0].readyState === "ended") {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        streamRef.current = stream;
      } else {
        stream = streamRef.current;
      }
      
      const recorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm', // More efficient format
      });
      
      mediaRecorderRef.current = recorder;
      
      recorder.ondataavailable = async (event: BlobEvent) => {
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN && event.data.size > 0) {
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
      
      recorder.start(100); // Collect audio in small chunks (100ms)
      setIsRecording(true);
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : String(error)}`);
      console.error("Error starting recording:", error);
    }
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
      setStatus("Ready to record");
    }
    
    // Pause tracks instead of stopping them completely
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    
    setIsRecording(false);
  };
  
  const cleanupResources = () => {
    // Clean up stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    
    // Clean up WebSocket
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.close();
    }
  };

  return (
    <div className="audio-capture">
      <h1>Audio Capture with Live Streaming</h1>
      <div className="status">Status: {status}</div>
      <button
        onClick={isRecording ? stopRecording : startRecording}
        disabled={!isConnected && !isRecording}
      >
        {isRecording ? "Stop Recording" : "Start Recording"}
      </button>
      {transcript && (
        <div className="transcript">
          <h3>Transcript:</h3>
          <p>{transcript}</p>
          <button onClick={() => setTranscript("")}>Clear</button>
        </div>
      )}
    </div>
  );
};

export default AudioCapture;