# NFCReader.cs オリジナルバックアップ

変更前の元のコード（`NFCReader copy.cs` の内容）。
復元する場合は以下をコピーして `NFCReader.cs` に貼り付けること。

```csharp
using UnityEngine;
using System;
using System.Threading;
using System.Threading.Tasks;
using PCSC;
using PCSC.Iso7816;
using PCSC.Monitoring;

public class NFCReader : MonoBehaviour
{
    private ISCardContext context;
    private ISCardMonitor monitor;
    private string mainReaderName;
    private SynchronizationContext mainThreadContext;
    private bool isQuitting = false;
    private bool isProcessing = false; // 読み取り中フラグ

    public Action<string> ActionOnReadCard;
    public Action<int> ActionOnReadTransportationICCard;
    public Action ActionOnReleaseCard;

    void Start()
    {
        mainThreadContext = SynchronizationContext.Current;
        try
        {
            context = ContextFactory.Instance.Establish(SCardScope.System);
            string[] readers = context.GetReaders();
            if (readers == null || readers.Length <= 0)
            {
                Debug.LogError("NFCリーダーが見つかりません");
                return;
            }

            mainReaderName = readers[0];
            monitor = MonitorFactory.Instance.Create(SCardScope.System);
            monitor.StatusChanged += StatusChanged;
            monitor.Start(mainReaderName);
        }
        catch (Exception e) { Debug.LogWarning($"NFC Start Error: {e.Message}"); }
    }

    private void StatusChanged(object sender, StatusChangeEventArgs args)
    {
        if (isQuitting) return;

        // カードが離れたとき
        if (args.NewState == SCRState.Empty)
        {
            isProcessing = false; // フラグをリセット
            mainThreadContext.Post(_ => ActionOnReleaseCard?.Invoke(), null);
            return;
        }

        // カードが置かれたとき (まだ処理中でない場合)
        if (args.NewState.HasFlag(SCRState.Present) && !isProcessing)
        {
            isProcessing = true;
            // 重い処理を別スレッドで実行して処理落ちを防ぐ
            Task.Run(() => ProcessCardData());
        }
    }

    private void ProcessCardData()
    {
        if (context == null || !context.IsValid()) return;

        try
        {
            using (var reader = context.ConnectReader(mainReaderName, SCardShareMode.Shared, SCardProtocol.Any))
            {
                byte[] receiveBuffer = new byte[256];

                // UUID取得
                var apdu = new CommandApdu(IsoCase.Case2Short, reader.Protocol)
                {
                    CLA = 0xFF,
                    Instruction = InstructionCode.GetData,
                    P1 = 0x00,
                    P2 = 0x00,
                    Le = 0
                };
                int received = reader.Transmit(SCardPCI.GetPci(reader.Protocol), apdu.ToArray(), receiveBuffer);
                var res = new ResponseApdu(receiveBuffer, received, IsoCase.Case2Short, reader.Protocol);

                if (res.SW1 == 0x90)
                {
                    string uid = BitConverter.ToString(res.GetData());
                    mainThreadContext.Post(_ => ActionOnReadCard?.Invoke(uid), null);
                }

                // 残高取得 (Suica/Pasmo対応FeliCa用)
                // 使用するリーダー(PaSori等)によってAPDUコマンドが異なる場合があります
                byte[] selectFile = { 0xff, 0xA4, 0x00, 0x01, 0x02, 0x0f, 0x09 };
                reader.Transmit(SCardPCI.GetPci(reader.Protocol), selectFile, receiveBuffer);

                byte[] readBinary = { 0xff, 0xb0, 0x00, 0x00, 0x00 };
                received = reader.Transmit(SCardPCI.GetPci(reader.Protocol), readBinary, receiveBuffer);
                var resBal = new ResponseApdu(receiveBuffer, received, IsoCase.Case2Short, reader.Protocol);

                if (resBal.SW1 == 0x90 && resBal.HasData)
                {
                    byte[] data = resBal.GetData();
                    if (data.Length >= 12)
                    {
                        // 10, 11バイト目が残高(リトルエンディアン)
                        int balance = BitConverter.ToInt16(new byte[] { data[10], data[11] }, 0);
                        mainThreadContext.Post(_ => ActionOnReadTransportationICCard?.Invoke(balance), null);
                    }
                }
            }
        }
        catch (Exception e)
        {
            Debug.Log($"Card Process Error: {e.Message}");
            isProcessing = false; // エラー時は再度読み取れるようにする
        }
    }

    private void OnDestroy() => Cleanup(); // Unity6ではOnDestroyでのクリーンアップが確実
    private void OnApplicationQuit() { isQuitting = true; Cleanup(); }

    private void Cleanup()
    {
        if (monitor != null) { monitor.Cancel(); monitor.Dispose(); monitor = null; }
        if (context != null) { context.Dispose(); context = null; }
    }
}
```
