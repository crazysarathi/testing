import { useEffect, useState } from "react";

function App() {
  const [socket, setSocket] = useState(null);
  const [switches, setSwitches] = useState([false, false, false, false]);

  useEffect(() => {
    // const ws = new WebSocket(`ws://${window.location.hostname}:8000`);
    const ws = new WebSocket("ws://172.17.3.174:8000/ws");
    setSocket(ws);

    ws.onopen = () => {
      console.log("Connected");
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "UPDATE_SWITCHES") {
        setSwitches(data.payload);
      }

      console.log("data",data);
      
    };

    return () => ws.close();
  }, []);

  const toggleSwitch = (index) => {
    const updated = [...switches];
    updated[index] = !updated[index];

    setSwitches(updated);

    socket.send(
      JSON.stringify({
        type: "UPDATE_SWITCHES",
        payload: updated,
      }),
    );
  };

  return (
    <div style={{ padding: 20 }}>
      <h2>Application 1</h2>

      {switches.map((val, i) => (
        <button
          key={i}
          onClick={() => toggleSwitch(i)}
          style={{
            margin: 10,
            padding: 10,
            background: val ? "green" : "gray",
            color: "white",
          }}
        >
          Switch {i + 1} : {val ? "ON" : "OFF"}
        </button>
      ))}
    </div>
  );
}

export default App;
