using UnityEngine;
using UnityEngine.Video;

[CreateAssetMenu(fileName = "NewMonster", menuName = "NFCProject/MonsterData")]
public class MonsterData : ScriptableObject
{
    public string monsterName;
    public int minBalance; // oŒ»‚·‚éÅ¬‹àŠz
    public int maxBalance; // oŒ»‚·‚éÅ‘å‹àŠz
    public GameObject bgPrefab; // ‘Î‰‚·‚é”wŒi
    public VideoClip videoClip; // ‘Î‰‚·‚é“®‰æ
    public AudioClip monsterBgm; // ‘Î‰‚·‚éBGM
}