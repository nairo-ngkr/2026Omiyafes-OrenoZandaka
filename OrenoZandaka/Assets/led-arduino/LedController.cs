using System;
using System.Reflection;
using UnityEngine;

public enum LedEffect
{
    Idle,
    WaitCard,
    Reading,
    Success,
    Error
}

public enum LedColor
{
    Blue,
    Purple,
    Cyan,
    White,
    Red,
    Orange,
    Gold
}

public class LedController : MonoBehaviour
{
    [Header("LED Serial Settings")]
    [SerializeField] private string ledSerialPortName = "COM3";
    [SerializeField] private int ledSerialBaudRate = 115200;
    [SerializeField] private bool openLedSerialOnStart = true;
    [SerializeField] private bool turnOffLedOnQuit = true;
    [SerializeField] private bool logLedCommands = true;

    private object ledSerialPort;
    private Type ledSerialPortType;

    private void Start()
    {
        if (openLedSerialOnStart)
        {
            OpenLedSerialPort();
        }
    }

    private void OnDestroy()
    {
        TurnOffLedAndCloseSerialPort();
    }

    private void OnApplicationQuit()
    {
        TurnOffLedAndCloseSerialPort();
    }

    public void OpenLedSerialPort()
    {
        try
        {
            if (ledSerialPort != null && IsLedSerialPortOpen())
            {
                return;
            }

            ledSerialPortType = GetSerialPortType();
            if (ledSerialPortType == null)
            {
                Debug.LogError("System.IO.Ports.SerialPort is not available. Set Api Compatibility Level to .NET Framework in Project Settings > Player.");
                return;
            }

            ledSerialPort = Activator.CreateInstance(ledSerialPortType, ledSerialPortName, ledSerialBaudRate);
            SetSerialPortProperty("NewLine", "\n");
            SetSerialPortProperty("ReadTimeout", 50);
            SetSerialPortProperty("WriteTimeout", 50);

            InvokeSerialPortMethod("Open");

            if (logLedCommands)
            {
                Debug.Log("LED serial connected: " + ledSerialPortName);
            }
        }
        catch (Exception exception)
        {
            Debug.LogError("Failed to open LED serial port: " + exception.Message);
        }
    }

    public void CloseLedSerialPort()
    {
        try
        {
            if (ledSerialPort == null)
            {
                return;
            }

            if (IsLedSerialPortOpen())
            {
                InvokeSerialPortMethod("Close");

                if (logLedCommands)
                {
                    Debug.Log("LED serial closed");
                }
            }

            InvokeSerialPortMethod("Dispose");
            ledSerialPort = null;
            ledSerialPortType = null;
        }
        catch (Exception exception)
        {
            Debug.LogWarning("Failed to close LED serial port: " + exception.Message);
        }
    }

    public void SendLedCommand(string command)
    {
        if (ledSerialPort == null || !IsLedSerialPortOpen())
        {
            Debug.LogWarning("LED serial port is not open");
            return;
        }

        try
        {
            InvokeSerialPortMethod("WriteLine", command);

            if (logLedCommands)
            {
                Debug.Log("Send to LED controller: " + command);
            }
        }
        catch (Exception exception)
        {
            Debug.LogError("LED serial write failed: " + exception.Message);
        }
    }

    public void PlayLedEffect(LedEffect effect)
    {
        switch (effect)
        {
            case LedEffect.Idle:
                PlayLedIdleEffect();
                break;
            case LedEffect.WaitCard:
                PlayLedWaitCardEffect();
                break;
            case LedEffect.Reading:
                PlayLedReadingEffect();
                break;
            case LedEffect.Success:
                PlayLedSuccessEffect();
                break;
            case LedEffect.Error:
                PlayLedErrorEffect();
                break;
            default:
                Debug.LogWarning("Unknown LED effect: " + effect);
                break;
        }
    }

    public void PlayLedIdleEffect()
    {
        SendLedCommand("STATE:IDLE");
    }

    public void PlayLedWaitCardEffect()
    {
        SendLedCommand("STATE:WAIT_CARD");
    }

    public void PlayLedReadingEffect()
    {
        SendLedCommand("STATE:READING");
    }

    public void PlayLedSuccessEffect()
    {
        SendLedCommand("STATE:SUCCESS");
    }

    public void PlayLedErrorEffect()
    {
        SendLedCommand("STATE:ERROR");
    }

    public void TurnOffLed()
    {
        SendLedCommand("STATE:OFF");
    }

    public void SetLedBrightness(int brightness)
    {
        int clampedBrightness = Mathf.Clamp(brightness, 0, 255);
        SendLedCommand("BRIGHTNESS:" + clampedBrightness);
    }

    public void SetLedColor(LedColor color)
    {
        SendLedCommand("COLOR:" + GetLedColorCommandName(color));
    }

    public void PingLedController()
    {
        SendLedCommand("PING");
    }

    private void TurnOffLedAndCloseSerialPort()
    {
        if (turnOffLedOnQuit && ledSerialPort != null && IsLedSerialPortOpen())
        {
            TurnOffLed();
        }

        CloseLedSerialPort();
    }

    private static string GetLedColorCommandName(LedColor color)
    {
        switch (color)
        {
            case LedColor.Blue:
                return "BLUE";
            case LedColor.Purple:
                return "PURPLE";
            case LedColor.Cyan:
                return "CYAN";
            case LedColor.White:
                return "WHITE";
            case LedColor.Red:
                return "RED";
            case LedColor.Orange:
                return "ORANGE";
            case LedColor.Gold:
                return "GOLD";
            default:
                return "CYAN";
        }
    }

    private static Type GetSerialPortType()
    {
        Type serialPortType = Type.GetType("System.IO.Ports.SerialPort, System");
        if (serialPortType != null)
        {
            return serialPortType;
        }

        serialPortType = Type.GetType("System.IO.Ports.SerialPort, System.IO.Ports");
        if (serialPortType != null)
        {
            return serialPortType;
        }

        Assembly[] assemblies = AppDomain.CurrentDomain.GetAssemblies();
        for (int i = 0; i < assemblies.Length; i++)
        {
            serialPortType = assemblies[i].GetType("System.IO.Ports.SerialPort");
            if (serialPortType != null)
            {
                return serialPortType;
            }
        }

        return null;
    }

    private bool IsLedSerialPortOpen()
    {
        if (ledSerialPort == null || ledSerialPortType == null)
        {
            return false;
        }

        PropertyInfo property = ledSerialPortType.GetProperty("IsOpen");
        return property != null && (bool)property.GetValue(ledSerialPort, null);
    }

    private void SetSerialPortProperty(string propertyName, object value)
    {
        PropertyInfo property = ledSerialPortType.GetProperty(propertyName);
        if (property != null)
        {
            property.SetValue(ledSerialPort, value, null);
        }
    }

    private void InvokeSerialPortMethod(string methodName)
    {
        MethodInfo method = ledSerialPortType.GetMethod(methodName, Type.EmptyTypes);
        if (method != null)
        {
            method.Invoke(ledSerialPort, null);
        }
    }

    private void InvokeSerialPortMethod(string methodName, string value)
    {
        MethodInfo method = ledSerialPortType.GetMethod(methodName, new[] { typeof(string) });
        if (method != null)
        {
            method.Invoke(ledSerialPort, new object[] { value });
        }
    }
}
