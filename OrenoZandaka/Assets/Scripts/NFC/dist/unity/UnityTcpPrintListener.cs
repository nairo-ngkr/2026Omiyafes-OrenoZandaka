using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using UnityEngine.Events;

/// <summary>
/// Python 側 run_local_print.py から届く JSON Lines を TCP で待ち受ける。
/// Unity から印刷要求は送らず、受信したイベントを UI/演出に使う。
/// </summary>
public class UnityTcpPrintListener : MonoBehaviour
{
    private const string DefaultRandomBalanceUid = "010101128F21C700";

    [SerializeField] private int listenPort = 9000;
    [SerializeField] private bool listenAnyAddress = true;
    [SerializeField] private bool logRawJson = true;
    [Header("Random Balance UID Settings")]
    [SerializeField] private bool randomBalanceEnabled = true;
    [SerializeField] private string[] randomBalanceUids = { DefaultRandomBalanceUid };
    [SerializeField] private int randomBalanceMin = 0;
    [SerializeField] private int randomBalanceMax = 20000;
    [SerializeField] private int randomBalanceCooldownSeconds = 50;
    [SerializeField] private UnityEvent<string> onJsonReceived;

    private readonly ConcurrentQueue<string> receivedJson = new ConcurrentQueue<string>();
    private TcpListener listener;
    private Thread listenerThread;
    private volatile bool running;

    public int ListenPort => listenPort;
    public bool RandomBalanceEnabled => randomBalanceEnabled;
    public string[] RandomBalanceUids => randomBalanceUids;
    public int RandomBalanceMin => randomBalanceMin;
    public int RandomBalanceMax => randomBalanceMax;
    public int RandomBalanceCooldownSeconds => randomBalanceCooldownSeconds;

    private void OnValidate()
    {
        EnsureRandomBalanceDefaults();
        WriteRandomBalanceConfig();
    }

    private void OnEnable()
    {
        EnsureRandomBalanceDefaults();
        WriteRandomBalanceConfig();
        StartListener();
    }

    private void OnDisable()
    {
        StopListener();
    }

    private void Update()
    {
        while (receivedJson.TryDequeue(out string json))
        {
            if (logRawJson)
            {
                Debug.Log($"[UnityTcpPrintListener] {json}");
            }

            onJsonReceived?.Invoke(json);
        }
    }

    public void StartListener()
    {
        if (running)
        {
            return;
        }

        IPAddress address = listenAnyAddress ? IPAddress.Any : IPAddress.Loopback;
        listener = new TcpListener(address, listenPort);
        listener.Start();
        running = true;

        listenerThread = new Thread(ListenLoop)
        {
            IsBackground = true,
            Name = "UnityTcpPrintListener"
        };
        listenerThread.Start();

        Debug.Log($"[UnityTcpPrintListener] listening tcp://{address}:{listenPort}");
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
            // Stop 中のソケット例外は終了処理として扱う。
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
                using TcpClient client = listener.AcceptTcpClient();
                using NetworkStream stream = client.GetStream();
                using StreamReader reader = new StreamReader(stream, Encoding.UTF8);

                string line;
                while (running && (line = reader.ReadLine()) != null)
                {
                    if (!string.IsNullOrWhiteSpace(line))
                    {
                        receivedJson.Enqueue(line);
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
                // listener.Stop() で抜けるときに発生する。
            }
            catch (IOException exc)
            {
                if (running)
                {
                    receivedJson.Enqueue($"{{\"event\":\"error\",\"error\":\"{EscapeJson(exc.Message)}\"}}");
                }
            }
        }
    }

    private static string EscapeJson(string value)
    {
        return value.Replace("\\", "\\\\").Replace("\"", "\\\"");
    }

    private void EnsureRandomBalanceDefaults()
    {
        if (randomBalanceUids == null || randomBalanceUids.Length == 0)
        {
            randomBalanceUids = new[] { DefaultRandomBalanceUid };
        }
    }

    private void WriteRandomBalanceConfig()
    {
        try
        {
            string configPath = Path.Combine(Application.dataPath, "Scripts", "NFC", "dist", "random_balance_config.json");
            string directory = Path.GetDirectoryName(configPath);
            if (!string.IsNullOrEmpty(directory))
            {
                Directory.CreateDirectory(directory);
            }

            StringBuilder builder = new StringBuilder();
            builder.AppendLine("{");
            builder.AppendLine($"  \"enabled\": {randomBalanceEnabled.ToString().ToLowerInvariant()},");
            builder.AppendLine("  \"uids\": [");
            for (int i = 0; i < randomBalanceUids.Length; i++)
            {
                string suffix = i + 1 < randomBalanceUids.Length ? "," : "";
                builder.AppendLine($"    \"{EscapeJson(randomBalanceUids[i] ?? string.Empty)}\"{suffix}");
            }
            builder.AppendLine("  ],");
            builder.AppendLine($"  \"min\": {randomBalanceMin},");
            builder.AppendLine($"  \"max\": {randomBalanceMax},");
            builder.AppendLine($"  \"cooldown_seconds\": {randomBalanceCooldownSeconds}");
            builder.AppendLine("}");
            File.WriteAllText(configPath, builder.ToString(), Encoding.UTF8);
        }
        catch (Exception exc)
        {
            Debug.LogWarning($"[UnityTcpPrintListener] random balance config write failed: {exc.Message}");
        }
    }
}
