using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using UnityEngine;

public class NFCReader : MonoBehaviour
{
    [Header("Python NFC TCP Settings")]
    [SerializeField] private int listenPort = 9000;
    [SerializeField] private bool listenAnyAddress = true;
    [SerializeField] private bool logRawJson = true;
    [SerializeField] private bool logIgnoredEvents = false;
    [SerializeField] private float autoReleaseSeconds = 0f;

    private readonly ConcurrentQueue<string> receivedJson = new ConcurrentQueue<string>();
    private TcpListener listener;
    private Thread listenerThread;
    private volatile bool running;
    private bool hasActiveCard;
    private float lastDetectedTime;

    public Action<string> ActionOnReadCard;
    public Action<int> ActionOnReadTransportationICCard;
    public Action ActionOnDetectedCard;
    public Action ActionOnReadFailedCard;
    public Action ActionOnReleaseCard;

    public int ListenPort => listenPort;

    private void Start()
    {
        StartListener();
    }

    private void Update()
    {
        while (receivedJson.TryDequeue(out string json))
        {
            if (logRawJson)
            {
                Debug.Log($"[NFCReader] {json}");
            }

            HandleJson(json);
        }

        if (hasActiveCard && autoReleaseSeconds > 0f && Time.time - lastDetectedTime >= autoReleaseSeconds)
        {
            hasActiveCard = false;
            ActionOnReleaseCard?.Invoke();
        }
    }

    private void OnDestroy()
    {
        StopListener();
    }

    private void OnApplicationQuit()
    {
        StopListener();
    }

    public void StartListener()
    {
        if (running)
        {
            return;
        }

        try
        {
            IPAddress address = listenAnyAddress ? IPAddress.Any : IPAddress.Loopback;
            listener = new TcpListener(address, listenPort);
            listener.Start();
            running = true;

            listenerThread = new Thread(ListenLoop)
            {
                IsBackground = true,
                Name = "NFCReaderTcpListener"
            };
            listenerThread.Start();

            Debug.Log($"[NFCReader] listening tcp://{address}:{listenPort}");
        }
        catch (Exception e)
        {
            Debug.LogError($"[NFCReader] Failed to start TCP listener: {e.Message}");
            ActionOnReadFailedCard?.Invoke();
        }
    }

    public void StopListener()
    {
        running = false;

        try
        {
            listener?.Stop();
        }
        catch (SocketException)
        {
        }

        if (listenerThread != null && listenerThread.IsAlive)
        {
            listenerThread.Join(500);
        }

        listenerThread = null;
        listener = null;
    }

    private void ListenLoop()
    {
        while (running)
        {
            try
            {
                using (TcpClient client = listener.AcceptTcpClient())
                using (NetworkStream stream = client.GetStream())
                using (StreamReader reader = new StreamReader(stream, Encoding.UTF8))
                {
                    string line;
                    while (running && (line = reader.ReadLine()) != null)
                    {
                        if (!string.IsNullOrWhiteSpace(line))
                        {
                            receivedJson.Enqueue(line);
                        }
                    }
                }
            }
            catch (SocketException)
            {
                if (running)
                {
                    receivedJson.Enqueue("{\"event\":\"error\",\"error\":\"TCP listener socket error\"}");
                }
            }
            catch (ObjectDisposedException)
            {
            }
            catch (IOException e)
            {
                if (running)
                {
                    receivedJson.Enqueue($"{{\"event\":\"error\",\"error\":\"{EscapeJson(e.Message)}\"}}");
                }
            }
        }
    }

    private void HandleJson(string json)
    {
        string eventName = GetJsonString(json, "event");
        string type = GetJsonString(json, "type");

        if (string.Equals(eventName, "error", StringComparison.OrdinalIgnoreCase))
        {
            Debug.LogWarning($"[NFCReader] Python NFC error: {GetJsonString(json, "error")}");
            ActionOnReadFailedCard?.Invoke();
            return;
        }

        if (IsReleaseEvent(eventName, type))
        {
            hasActiveCard = false;
            ActionOnReleaseCard?.Invoke();
            return;
        }

        if (!IsDetectionEvent(eventName, type))
        {
            if (logIgnoredEvents)
            {
                Debug.Log($"[NFCReader] Ignored TCP event: {json}");
            }

            return;
        }

        string uid = FirstNonEmpty(
            GetJsonString(json, "uid"),
            GetJsonString(json, "idm"),
            GetJsonString(json, "card_uid"));

        if (!TryGetJsonInt(json, "balance", out int balance) &&
            !TryGetJsonInt(json, "value", out balance) &&
            !TryGetJsonInt(json, "balance_int", out balance))
        {
            Debug.LogWarning("[NFCReader] NFC event does not contain a readable balance.");
            ActionOnReadFailedCard?.Invoke();
            return;
        }

        if (string.IsNullOrEmpty(uid))
        {
            uid = $"PYTHON_NFC_{balance}";
        }

        hasActiveCard = true;
        lastDetectedTime = Time.time;

        ActionOnDetectedCard?.Invoke();
        ActionOnReadCard?.Invoke(uid);
        ActionOnReadTransportationICCard?.Invoke(balance);
    }

    private static bool IsDetectionEvent(string eventName, string type)
    {
        return string.Equals(eventName, "detected", StringComparison.OrdinalIgnoreCase) ||
               string.Equals(type, "transit", StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsReleaseEvent(string eventName, string type)
    {
        return string.Equals(eventName, "released", StringComparison.OrdinalIgnoreCase) ||
               string.Equals(eventName, "release", StringComparison.OrdinalIgnoreCase) ||
               string.Equals(type, "released", StringComparison.OrdinalIgnoreCase) ||
               string.Equals(type, "release", StringComparison.OrdinalIgnoreCase);
    }

    private static string FirstNonEmpty(params string[] values)
    {
        for (int i = 0; i < values.Length; i++)
        {
            if (!string.IsNullOrEmpty(values[i]))
            {
                return values[i];
            }
        }

        return "";
    }

    private static string GetJsonString(string json, string key)
    {
        Match match = Regex.Match(
            json,
            $"\"{Regex.Escape(key)}\"\\s*:\\s*\"(?<value>(?:\\\\.|[^\"])*)\"",
            RegexOptions.CultureInvariant);

        return match.Success ? UnescapeJsonString(match.Groups["value"].Value) : "";
    }

    private static bool TryGetJsonInt(string json, string key, out int value)
    {
        Match numberMatch = Regex.Match(
            json,
            $"\"{Regex.Escape(key)}\"\\s*:\\s*(?<value>-?\\d+)",
            RegexOptions.CultureInvariant);

        if (numberMatch.Success && int.TryParse(numberMatch.Groups["value"].Value, out value))
        {
            return true;
        }

        string stringValue = GetJsonString(json, key);
        return int.TryParse(stringValue, out value);
    }

    private static string UnescapeJsonString(string value)
    {
        return value
            .Replace("\\\"", "\"")
            .Replace("\\\\", "\\")
            .Replace("\\/", "/")
            .Replace("\\n", "\n")
            .Replace("\\r", "\r")
            .Replace("\\t", "\t");
    }

    private static string EscapeJson(string value)
    {
        return value.Replace("\\", "\\\\").Replace("\"", "\\\"");
    }
}
