using UnityEngine;
using System.Collections.Generic;
using UnityEngine.InputSystem;
using UnityEngine.Video;
using System.Linq;
using TMPro;
using UnityEngine.UI;
using DG.Tweening;

public class MonsterManager : MonoBehaviour
{
    [Header("基本設定")]
    public NFCReader nfcReader;
    public LedController ledController;
    public Transform bgParent;
    public VideoPlayer globalVideoPlayer; // モンスター用のVideoPlayer（クロマキー側）
    public List<MonsterData> allMonsters;
    [Tooltip("ぞろ目の時に出現させるレアモンスターを指定")]
    public MonsterData rareMonsterData;
    private GameObject currentSpawnedBG;

    [Header("オーディオ設定")]
    public AudioSource bgmAudioSource;       // 音を鳴らすためのコンポーネント
    public AudioClip standbyBgm;             // 待機画面用の音（ループBGMなど）

    [Header("待機画面設定")]
    public GameObject standbyUiPanel;        // 待機画面用のUIパネル（RawImageなどが入った親）
    public VideoPlayer standbyVideoPlayer;    // 待機画面専用のVideoPlayer（クロマキー処理なし）
    public GameObject standbyLogoUiPanel;    // 待機画面用のデカいロゴUI

    [Header("左上：ロゴUI設定（モンスター登場中）")]
    public GameObject logoUiPanel;           // モンスター登場中のロゴオブジェクト

    [Header("左下：累計ステータスUI")]
    public GameObject totalUiPanel;
    public TextMeshProUGUI totalHpText;
    public Slider totalHpSlider;
    public TextMeshProUGUI totalMpText;
    public Slider totalMpSlider;

    [Header("右側：個別モンスターステータスUI")]
    public GameObject individualUiPanel;
    public TextMeshProUGUI mNameText;
    public TextMeshProUGUI mLevelText;
    public TextMeshProUGUI mHpText;
    public Slider mHpSlider;
    public TextMeshProUGUI mMpText;
    public Slider mMpSlider;

    [Space(10)]
    public TextMeshProUGUI atkText;
    public TextMeshProUGUI defText;
    public TextMeshProUGUI spdText;

    [Header("画面右下：アイテム欄UI切り替え設定")]
    public GameObject itemBarPanel;          // 親オブジェクト（Item_Panel）
    public GameObject normalItemObject;      // 通常時の画像が入ったオブジェクト
    public GameObject secretItemObject;      // レア時の画像が入ったオブジェクト

    [Header("属性別ランダムテキスト設定")]
    public string[] atkPhrases = {
        "静電気で「イッ」ってなるくらい", "紙で指切るくらい", "ささくれ引っぱったくらい",
        "口内えんにポテチささるくらい", "つめ切りすぎたくらい", "目にシャンプー入ったくらい",
        "ねちがえた朝くらい", "レゴふんだ時ぐらい", "あげ油はねたくらい",
        "歯医者で「ちょっとしみますね」くらい", "くつずれのじょうたいで走るくらい",
        "画びょうに気づかずすわるくらい", "クラス全員静かな時におなか鳴るくらい（せいしん的ダメージ）",
        "名前まちがえてよんだくらい（せいしん的ダメージ）"
    };
    public string[] defPhrases = {
        "しめったティッシュくらい", "コンビニのスプーンくらい", "初期そうびの「木のたて」くらい",
        "風強い日にかさを差したくらい", "とうふくらい（メンタルも）", "スマホのほごフィルムくらい",
        "ダンボール二重にしたくらい", "国語辞典くらい", "工事用のヘルメットくらい",
        "トラックにはね飛ばされてもノーダメ", "象がふんでもこわれない筆箱",
        "黒歴史を「まぁわかかったし」ですませるくらい", "LINE未読スルーをノーダメ",
        "店員に聞き返されても折れない", "プレゼン中にかんでも続行できる"
    };
    public string[] spdPhrases = {
        "レジ前でお金をさがす人くらい", "エレベーターの「しめる」ボタン連打してる時くらい",
        "ちこくしそうな学生くらい", "電車来たときの階だんダッシュくらい", "シャトルラン30回目くらい",
        "チケット予約開始直後の通信速度くらい", "始発でコミケに向かうオタクくらい",
        "野球選手のストレートくらい", "林間学校の消灯後の男子くらい", "セール会場のおばちゃんくらい",
        "黒歴史思い出した時ののう内速度", "「先生来た！」って聞いた男子くらい",
        "親の足音聞こえた時くらい", "熱いなべさわった時くらい", "テスト返きゃく前の心ぱく数くらい"
    };

    [Header("目標設定")]
    public long totalHpGoal = 500000;
    public int totalMpGoal = 250;

    private long totalBalanceSum = 0;
    private int totalVisitorCount = 0;
    private HashSet<string> readUUIDs = new HashSet<string>();
    private string currentCardUID = "";

    private long dispTotalHp, dispTotalMp, dispIndivHp, dispIndivMp;
    private readonly int[] rareNumbers = { 124, 555, 666, 777, 888, 999, 1111, 2222, 3333, 4444, 5555, 6666, 7777, 8888, 9999, 11111 };

    [Header("演出維持設定")]
    [Tooltip("カードタッチ後、最低限この秒数は演出を維持する（50秒）")]
    public float minDisplaySeconds = 50f;
    private bool cardPhysicallyReleased = false;
    private float displayStartTime = 0f;
    private bool isDisplaying = false;

    private Vector3 originalLogoScale;
    private Vector3 originalIndividualScale;

    [Header("デバッグ設定")]
    [Range(0f, 100f), Tooltip("0キーを押した時にレアモンスターが出現する確率（%）")]
    public float rareSpawnChance = 5f;

    [Tooltip("チェックを入れると、0キーでも累計カウント（HP/MP）を増やす")]
    public bool countDebugZero = true; // 初期値はオン（カウントする）

    void Start()
    {
        if (globalVideoPlayer != null) globalVideoPlayer.prepareCompleted += OnVideoPrepared;
        if (totalUiPanel != null) totalUiPanel.SetActive(true);
        if (individualUiPanel != null) individualUiPanel.SetActive(false);
        if (itemBarPanel != null) itemBarPanel.SetActive(false);
        if (logoUiPanel != null) logoUiPanel.SetActive(false);

        if (logoUiPanel != null) originalLogoScale = logoUiPanel.transform.localScale;
        if (individualUiPanel != null) originalIndividualScale = individualUiPanel.transform.localScale;

        if (totalHpSlider != null) totalHpSlider.maxValue = totalHpGoal;
        if (totalMpSlider != null) totalMpSlider.maxValue = totalMpGoal;

        totalVisitorCount = PlayerPrefs.GetInt("TotalVisitors", 0);
        long.TryParse(PlayerPrefs.GetString("TotalBalanceSum", "0"), out totalBalanceSum);

        UpdateTotalUI(true);

        // 待機画面の初期再生
        if (standbyUiPanel != null) standbyUiPanel.SetActive(true);
        if (standbyLogoUiPanel != null) standbyLogoUiPanel.SetActive(true);
        if (standbyVideoPlayer != null)
        {
            standbyVideoPlayer.isLooping = true;
            standbyVideoPlayer.Play();
        }

        PlayBgm(standbyBgm, true);
        PlayLedWaitCard();
    }

    void OnEnable()
    {
        if (nfcReader != null)
        {
            nfcReader.ActionOnReadCard += HandleCardRead;
            nfcReader.ActionOnDetectedCard += HandleCardDetected;
            nfcReader.ActionOnReadTransportationICCard += HandleBalanceReadNormal;
            nfcReader.ActionOnReadFailedCard += HandleCardReadFailed;
            nfcReader.ActionOnReleaseCard += HandleCardReleased;
        }
    }

    void OnDisable()
    {
        if (nfcReader != null)
        {
            nfcReader.ActionOnReadCard -= HandleCardRead;
            nfcReader.ActionOnDetectedCard -= HandleCardDetected;
            nfcReader.ActionOnReadTransportationICCard -= HandleBalanceReadNormal;
            nfcReader.ActionOnReadFailedCard -= HandleCardReadFailed;
            nfcReader.ActionOnReleaseCard -= HandleCardReleased;
        }
    }

    private void HandleCardRead(string uid)
    {
        currentCardUID = uid;
    }

    private void HandleCardDetected()
    {
        PlayLedReading();
    }

    private void HandleCardReadFailed()
    {
        PlayLedError();
    }

    void Update()
    {
        if (isDisplaying && cardPhysicallyReleased && Time.time - displayStartTime >= minDisplaySeconds)
        {
            EndDisplay();
        }

        var keyboard = Keyboard.current;
        if (keyboard == null) return;

        // --- リセット処理 (Shift + Ctrl + R) ---
        if (keyboard.shiftKey.isPressed && keyboard.ctrlKey.isPressed && keyboard.rKey.wasPressedThisFrame)
        {
            ResetAllData();
            return;
        }

        // --- デバッグ疑似残高召喚 (0キー)  ---
        if (keyboard.digit0Key.wasPressedThisFrame)
        {
            // 0キーを連続で押した際も都度カウントさせるため、毎回異なる擬似的なUIDを生成して重複ガードを回避
            currentCardUID = "Debug_Key_Zero_Fake_" + System.Guid.NewGuid().ToString();

            cardPhysicallyReleased = false; // 擬似的にカードが置かれている状態として扱う
            if (totalUiPanel != null) totalUiPanel.SetActive(true); // 累計UIを強制復帰

            int fakeBalance = 0;

            // --- 確率判定（0.0 〜 100.0 の乱数を生成） ---
            float randomRoll = Random.Range(0f, 100f);

            if (randomRoll <= rareSpawnChance)
            {
                // 【確率クリア】シークレット（レア）が選ばれた場合
                fakeBalance = rareNumbers[Random.Range(0, rareNumbers.Length)];
                Debug.Log($"<color=cyan>[Debug0] 確率抽選（{rareSpawnChance}%）：シークレットキャラが選ばれました！ (出目: {randomRoll:F1})</color>");
            }
            else
            {
                // 【確率外】通常モンスターのリストから等確率でランダムに選ぶ
                int randomIndex = Random.Range(0, allMonsters.Count);
                MonsterData targetMonster = allMonsters[randomIndex];
                fakeBalance = Random.Range(targetMonster.minBalance, targetMonster.maxBalance + 1);
                Debug.Log($"<color=cyan>[Debug0] 確率抽選：【{targetMonster.monsterName}】が選ばれました。 (出目: {randomRoll:F1})</color>");
            }

            // チェックボックスの状態に応じてカウントするかを自動で切り替える（countDebugZero：true(オン) →HandleBalanceRead：false(制限解除)が渡りカウント）
            HandleBalanceRead(fakeBalance, !countDebugZero);
        }

        // デバッグ召喚 (1～7)
        for (int i = 0; i < 7; i++)
        {
            Key key = (Key)((int)Key.Digit1 + i);
            CheckDebugKey(keyboard, key, i);
        }

        // デバッグ召喚 (8: シークレット)
        if (keyboard[Key.Digit8].wasPressedThisFrame)
        {
            currentCardUID = "Debug_Key_Secret";
            HandleBalanceRead(777, false);
        }
    }

    private void CheckDebugKey(Keyboard k, Key key, int index)
    {
        if (k[key].wasPressedThisFrame && index < allMonsters.Count)
        {
            currentCardUID = "Debug_Key_" + index;
            HandleBalanceRead(allMonsters[index].minBalance, false);
        }
    }

    // NFC読み取りイベントから通常時（累計追加あり）として呼び出すためのブリッジ
    private void HandleBalanceReadNormal(int balance)
    {
        HandleBalanceRead(balance, false);
    }

    // 実際の処理ロジック (isDebugZeroがtrueの時は、累計加算をスキップして現状維持)
    private void HandleBalanceRead(int balance, bool isDebugZero)
    {
        // 0キーデバッグではない場合のみ、来場者カウント（重複防止）を行う
        if (!isDebugZero)
        {
            if (!string.IsNullOrEmpty(currentCardUID) && !readUUIDs.Contains(currentCardUID))
            {
                readUUIDs.Add(currentCardUID);
                totalVisitorCount++;
                totalBalanceSum += balance;

                PlayerPrefs.SetInt("TotalVisitors", totalVisitorCount);
                PlayerPrefs.SetString("TotalBalanceSum", totalBalanceSum.ToString());
                UpdateTotalUI(false);
            }
        }
        else
        {
            Debug.Log($"<color=cyan>[Debug0] 疑似残高 {balance}円 で召喚判定（累計HP/MPは現状維持）</color>");
        }

        // 2. モンスター判定
        MonsterData hitMonster = null;
        bool isSecret = false;

        if (rareNumbers.Contains(balance))
        {
            hitMonster = rareMonsterData;
            isSecret = true;
        }
        else
        {
            hitMonster = allMonsters.FirstOrDefault(m => balance >= m.minBalance && balance <= m.maxBalance);
        }

        if (hitMonster != null)
        {
            if (standbyUiPanel != null) standbyUiPanel.SetActive(false);
            if (standbyLogoUiPanel != null) standbyLogoUiPanel.SetActive(false);
            if (standbyVideoPlayer != null) standbyVideoPlayer.Stop();

            SpawnMonster(hitMonster);
            UpdateIndividualUI(balance, hitMonster, isSecret);

            PlayBgm(hitMonster.monsterBgm, true);
            PlayLedSuccess();

            displayStartTime = Time.time;
            cardPhysicallyReleased = false;
            isDisplaying = true;
        }
        else
        {
            // 0キーのランダムで該当モンスターがいなかった場合もエラーLEDを回す
            PlayLedError();
            if (isDebugZero)
            {
                Debug.LogWarning($"疑似残高 {balance}円 に対応するモンスターの範囲がallMonsters内に定義されていません。");
            }
        }
    }

    private void ResetAllData()
    {
        totalVisitorCount = 0;
        totalBalanceSum = 0;
        readUUIDs.Clear();

        PlayerPrefs.DeleteKey("TotalVisitors");
        PlayerPrefs.DeleteKey("TotalBalanceSum");
        PlayerPrefs.Save();

        UpdateTotalUI(false);
        EndDisplay();

        Debug.Log("<color=red>[MonsterManager] すべての累計記録をリセットしました。</color>");
    }

    private void UpdateTotalUI(bool instant)
    {
        float duration = instant ? 0f : 0.8f;
        if (totalHpSlider != null) totalHpSlider.DOValue(totalBalanceSum, duration);

        DOTween.To(() => dispTotalHp, x => {
            dispTotalHp = x;
            if (totalHpText != null) totalHpText.text = $"HP: {dispTotalHp:N0}";
        }, totalBalanceSum, duration);

        if (totalMpSlider != null) totalMpSlider.DOValue(totalVisitorCount, duration);

        DOTween.To(() => dispTotalMp, x => {
            dispTotalMp = x;
            if (totalMpText != null) totalMpText.text = $"MP: {dispTotalMp:N0}";
        }, totalVisitorCount, duration);
    }

    private void UpdateIndividualUI(int balance, MonsterData data, bool isSecret)
    {
        if (individualUiPanel != null)
        {
            individualUiPanel.SetActive(true);
            individualUiPanel.transform.localScale = originalIndividualScale * 0.8f;
            individualUiPanel.transform.DOScale(originalIndividualScale, 0.3f).SetEase(Ease.OutBack);
        }

        if (logoUiPanel != null)
        {
            logoUiPanel.SetActive(true);
            logoUiPanel.transform.localScale = originalLogoScale * 0.8f;
            logoUiPanel.transform.DOScale(originalLogoScale, 0.3f).SetEase(Ease.OutBack);
        }

        if (itemBarPanel != null) itemBarPanel.SetActive(true);
        if (normalItemObject != null) normalItemObject.SetActive(!isSecret);
        if (secretItemObject != null) secretItemObject.SetActive(isSecret);

        if (mNameText != null) mNameText.text = data.monsterName;
        if (mLevelText != null) mLevelText.text = $"Lv.{balance / 100}";

        int maxHp = (data.maxBalance > 0) ? data.maxBalance : (int)(balance * 1.2f);
        if (mHpSlider != null) { mHpSlider.maxValue = maxHp; mHpSlider.DOValue(balance, 0.6f); }
        DOTween.To(() => dispIndivHp, x => {
            dispIndivHp = x;
            if (mHpText != null) mHpText.text = $"HP: {dispIndivHp}/{maxHp}";
        }, balance, 0.6f);

        int currentMp = balance / 5;
        int maxMp = maxHp / 5;
        if (mMpSlider != null) { mMpSlider.maxValue = maxMp; mMpSlider.DOValue(currentMp, 0.6f); }
        DOTween.To(() => dispIndivMp, x => {
            dispIndivMp = x;
            if (mMpText != null) mMpText.text = $"MP: {dispIndivMp}/{maxMp}";
        }, currentMp, 0.6f);

        if (atkText != null) atkText.text = $"こうげき力：{atkPhrases[Random.Range(0, atkPhrases.Length)]}";
        if (defText != null) defText.text = $"ぼうぎょ力：{defPhrases[Random.Range(0, defPhrases.Length)]}";
        if (spdText != null) spdText.text = $"すばやさ：{spdPhrases[Random.Range(0, spdPhrases.Length)]}";
    }

    private void HandleCardReleased()
    {
        cardPhysicallyReleased = true;
        if (!isDisplaying)
        {
            EndDisplay();
        }
    }

    private void EndDisplay()
    {
        isDisplaying = false;
        cardPhysicallyReleased = false;

        if (currentSpawnedBG != null) Destroy(currentSpawnedBG);
        if (globalVideoPlayer != null) globalVideoPlayer.Stop();
        if (individualUiPanel != null) individualUiPanel.SetActive(false);
        if (itemBarPanel != null) itemBarPanel.SetActive(false);
        if (logoUiPanel != null) logoUiPanel.SetActive(false);

        if (standbyUiPanel != null) standbyUiPanel.SetActive(true);
        if (standbyLogoUiPanel != null) standbyLogoUiPanel.SetActive(true);
        if (standbyVideoPlayer != null) standbyVideoPlayer.Play();

        PlayBgm(standbyBgm, true);
        currentCardUID = "";
        PlayLedWaitCard();
    }

    public void SpawnMonster(MonsterData data)
    {
        if (currentSpawnedBG != null) Destroy(currentSpawnedBG);
        if (data.bgPrefab != null)
        {
            currentSpawnedBG = Instantiate(data.bgPrefab, bgParent);
            currentSpawnedBG.transform.localPosition = Vector3.zero;
        }
        if (globalVideoPlayer != null && data.videoClip != null)
        {
            globalVideoPlayer.Stop();
            globalVideoPlayer.clip = data.videoClip;
            globalVideoPlayer.Prepare();
        }
    }

    private void OnVideoPrepared(VideoPlayer vp) => vp.Play();

    private void PlayBgm(AudioClip clip, bool loop)
    {
        if (bgmAudioSource == null) return;

        bgmAudioSource.Stop();
        if (clip != null)
        {
            bgmAudioSource.clip = clip;
            bgmAudioSource.loop = loop;
            bgmAudioSource.Play();
        }
    }

    private void PlayLedWaitCard()
    {
        if (ledController == null) return;
        ledController.OpenLedSerialPort();
        ledController.PlayLedWaitCardEffect();
    }

    private void PlayLedReading()
    {
        if (ledController == null) return;
        ledController.OpenLedSerialPort();
        ledController.PlayLedReadingEffect();
    }

    private void PlayLedSuccess()
    {
        if (ledController == null) return;
        ledController.OpenLedSerialPort();
        ledController.PlayLedSuccessEffect();
    }

    private void PlayLedError()
    {
        if (ledController == null) return;
        ledController.OpenLedSerialPort();
        ledController.PlayLedErrorEffect();
    }
}