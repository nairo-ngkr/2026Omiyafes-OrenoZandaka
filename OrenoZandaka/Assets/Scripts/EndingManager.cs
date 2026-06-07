using UnityEngine;
using System.Collections.Generic;
using UnityEngine.InputSystem;
using TMPro;
using UnityEngine.UI;
using DG.Tweening;

public class EndingManager : MonoBehaviour
{
    [Header("連動させるマネージャー")]
    public MonsterManager monsterManager;    // MonsterManagerをここにアタッチ

    [Header("モンスター動画を描画しているRawImage等")]
    [Tooltip("クロマキー動画(VideoMaterial/Texture)が表示されているRawImageオブジェクトをここに登録")]
    public GameObject globalVideoRawImage;  // 背景の前に出る動画用のUIオブジェクト

    [Header("エンディング全体パネル")]
    public GameObject endingCanvasPanel;     // エンディングUI全体をまとめる親オブジェクト

    [Header("エンディングUI要素")]
    public GameObject endingBgObject;        // エンディング用の背景画像
    public GameObject endingLogoObject;      // 左上のロゴ画像

    [Header("出現させるモンスター8体 (GameObject)")]
    [Tooltip("画面に並べる8体のモンスターUIオブジェクトを順番に登録")]
    public List<GameObject> endingMonsterObjects = new List<GameObject>();

    [Header("エンディング：累計ステータスUI")]
    public TextMeshProUGUI endingTotalHpText;
    public Slider endingTotalHpSlider;
    public TextMeshProUGUI endingTotalMpText;
    public Slider endingTotalMpSlider;

    [Header("目標設定（これまでの設定と同じ）")]
    public long totalHpGoal = 500000;
    public int totalMpGoal = 250;

    private bool isEndingActive = false;
    private long dispTotalHp;
    private int dispTotalMp;

    // 本来のエディタサイズ（Scale）を記憶する辞書
    private Dictionary<GameObject, Vector3> originalScales = new Dictionary<GameObject, Vector3>();
    private Vector3 originalLogoScale;
    private Vector3 originalBgScale;

    void Start()
    {
        // 最初はエンディング画面を隠しておく
        if (endingCanvasPanel != null) endingCanvasPanel.SetActive(false);

        // 各スライダーの最大値を設定
        if (endingTotalHpSlider != null) endingTotalHpSlider.maxValue = totalHpGoal;
        if (endingTotalMpSlider != null) endingTotalMpSlider.maxValue = totalMpGoal;

        // 本来のサイズ（Scale）を記憶する
        if (endingLogoObject != null) originalLogoScale = endingLogoObject.transform.localScale;
        if (endingBgObject != null) originalBgScale = endingBgObject.transform.localScale;

        foreach (var monster in endingMonsterObjects)
        {
            if (monster != null)
            {
                originalScales[monster] = monster.transform.localScale;
                monster.SetActive(false); // 最初は非表示に
            }
        }
    }

    void Update()
    {
        var keyboard = Keyboard.current;
        if (keyboard == null) return;

        // --- Nキーの状態を毎フレーム監視 ---
        if (keyboard.nKey.isPressed)
        {
            // Nキーが押されていて、まだエンディングが始まっていなければ開始
            if (!isEndingActive)
            {
                StartEnding();
            }
        }
        else
        {
            // Nキーが離されていて、エンディング画面がアクティブなら終了して待機画面へ戻す
            if (isEndingActive)
            {
                EndEnding();
            }
        }
    }

    private void StartEnding()
    {
        isEndingActive = true;
        Debug.Log("[EndingManager] Nキーホールド：エンディング画面を表示します");

        // 既存のTweenアニメーションを一度クリアしてバグを防ぐ
        DOTween.Kill(this);

        // 1. 既存のゲーム画面（待機画面、モンスター、BGM、各種UI）を強制的に全非表示＆停止にする
        if (monsterManager != null)
        {
            monsterManager.SendMessage("HandleCardReleased", SendMessageOptions.DontRequireReceiver);

            if (monsterManager.standbyUiPanel != null) monsterManager.standbyUiPanel.SetActive(false);
            if (monsterManager.standbyLogoUiPanel != null) monsterManager.standbyLogoUiPanel.SetActive(false);
            if (monsterManager.totalUiPanel != null) monsterManager.totalUiPanel.SetActive(false);
            if (monsterManager.individualUiPanel != null) monsterManager.individualUiPanel.SetActive(false);
            if (monsterManager.itemBarPanel != null) monsterManager.itemBarPanel.SetActive(false);
            if (monsterManager.logoUiPanel != null) monsterManager.logoUiPanel.SetActive(false);
            if (monsterManager.globalVideoPlayer != null) monsterManager.globalVideoPlayer.Stop();
            if (monsterManager.standbyVideoPlayer != null) monsterManager.standbyVideoPlayer.Stop();
            if (monsterManager.bgmAudioSource != null) monsterManager.bgmAudioSource.Stop();
        }

        if (globalVideoRawImage != null)
        {
            globalVideoRawImage.SetActive(false);
        }

        // 2. エンディング画面のルートを表示
        if (endingCanvasPanel != null) endingCanvasPanel.SetActive(true);

        // 3. 背景とロゴの演出
        if (endingBgObject != null)
        {
            endingBgObject.SetActive(true);
            endingBgObject.transform.localScale = originalBgScale * 0.9f;
            endingBgObject.transform.DOScale(originalBgScale, 0.5f).SetEase(Ease.OutCubic).SetLink(gameObject);
        }

        if (endingLogoObject != null)
        {
            endingLogoObject.SetActive(true);
            endingLogoObject.transform.localScale = originalLogoScale * 0.5f;
            endingLogoObject.transform.DOScale(originalLogoScale, 0.6f).SetDelay(0.2f).SetEase(Ease.OutBack).SetLink(gameObject);
        }

        // 4. データ読み込みと累計ステータスのアニメーション
        long totalBalanceSum = 0;
        int totalVisitorCount = PlayerPrefs.GetInt("TotalVisitors", 0);
        long.TryParse(PlayerPrefs.GetString("TotalBalanceSum", "0"), out totalBalanceSum);

        // 毎回「0」からカウントアップさせるため、演出開始時に表示用変数とUIをリセット
        dispTotalHp = 0;
        dispTotalMp = 0;
        if (endingTotalHpSlider != null) endingTotalHpSlider.value = 0;
        if (endingTotalMpSlider != null) endingTotalMpSlider.value = 0;
        if (endingTotalHpText != null) endingTotalHpText.text = "HP: 0";
        if (endingTotalMpText != null) endingTotalMpText.text = "MP: 0";

        AnimateEndingUI(totalBalanceSum, totalVisitorCount);

        // 5. 8体のモンスターを時間差（ディレイ）を設けて出現させる演出
        float currentDelay = 0.5f;
        foreach (var monster in endingMonsterObjects)
        {
            if (monster == null) continue;

            GameObject targetMonster = monster;
            Vector3 targetScale = originalScales[targetMonster];

            targetMonster.SetActive(false);
            targetMonster.transform.localScale = targetScale * 0.1f;

            DOVirtual.DelayedCall(currentDelay, () =>
            {
                if (isEndingActive)
                {
                    targetMonster.SetActive(true);
                    targetMonster.transform.DOScale(targetScale, 0.4f).SetEase(Ease.OutBack);
                }
            }).SetLink(gameObject);

            currentDelay += 0.15f;
        }
    }

    private void AnimateEndingUI(long targetHp, int targetMp)
    {
        float duration = 1.2f;

        if (endingTotalHpSlider != null) endingTotalHpSlider.DOValue(targetHp, duration).SetEase(Ease.OutQuad).SetLink(gameObject);
        DOTween.To(() => dispTotalHp, x => {
            dispTotalHp = x;
            if (endingTotalHpText != null) endingTotalHpText.text = $"HP（ごうけい）: {dispTotalHp:N0}";
        }, targetHp, duration).SetEase(Ease.OutQuad).SetLink(gameObject);

        if (endingTotalMpSlider != null) endingTotalMpSlider.DOValue(targetMp, duration).SetEase(Ease.OutQuad).SetLink(gameObject);
        DOTween.To(() => dispTotalMp, x => {
            dispTotalMp = x;
            if (endingTotalMpText != null) endingTotalMpText.text = $"MP（プレイすう）: {dispTotalMp:N0}";
        }, targetMp, duration).SetEase(Ease.OutQuad).SetLink(gameObject);
    }

    private void EndEnding()
    {
        if (!isEndingActive) return;
        isEndingActive = false;

        Debug.Log("[EndingManager] Nキーが離されたため、待機画面へ戻ります");

        // 実行中のエンディングTween演出を即座に破棄
        DOTween.Kill(this);

        // エンディングUI、背景、ロゴ、モンスターをすべて即座に非表示にする
        if (endingBgObject != null) endingBgObject.SetActive(false);
        if (endingLogoObject != null) endingLogoObject.SetActive(false);
        if (endingCanvasPanel != null) endingCanvasPanel.SetActive(false);

        foreach (var monster in endingMonsterObjects)
        {
            if (monster != null) monster.SetActive(false);
        }

        // MonsterManager側の初期待機状態への復帰処理を実行
        if (monsterManager != null)
        {
            if (globalVideoRawImage != null)
            {
                globalVideoRawImage.SetActive(true);
            }

            monsterManager.SendMessage("EndDisplay", SendMessageOptions.DontRequireReceiver);
        }
    }
}