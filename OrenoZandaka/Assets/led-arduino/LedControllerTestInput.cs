using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

public class LedControllerTestInput : MonoBehaviour
{
    [SerializeField] private LedController ledController;

    private readonly LedEffect[] ledEffectOrder =
    {
        LedEffect.Idle,
        LedEffect.WaitCard,
        LedEffect.Reading,
        LedEffect.Success,
        LedEffect.Error
    };

    private int currentLedEffectIndex = -1;

    private void Reset()
    {
        ledController = GetComponent<LedController>();
    }

    private void Awake()
    {
        if (ledController == null)
        {
            ledController = GetComponent<LedController>();
        }
    }

    private void Update()
    {
        if (WasNextLedEffectKeyPressed())
        {
            PlayNextLedEffect();
        }
    }

    public void PlayNextLedEffect()
    {
        if (ledController == null)
        {
            Debug.LogWarning("LedControllerTestInput: LedController is not assigned.");
            return;
        }

        currentLedEffectIndex = (currentLedEffectIndex + 1) % ledEffectOrder.Length;
        LedEffect effect = ledEffectOrder[currentLedEffectIndex];

        Debug.Log("LED test effect: " + effect);
        ledController.PlayLedEffect(effect);
    }

    private bool WasNextLedEffectKeyPressed()
    {
#if ENABLE_INPUT_SYSTEM
        return Keyboard.current != null && Keyboard.current.lKey.wasPressedThisFrame;
#else
        return Input.GetKeyDown(KeyCode.L);
#endif
    }
}
