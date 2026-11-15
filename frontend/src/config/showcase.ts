import inputs from '../../../input_data/john_showcase.json';

/** One saved input fixture supplies the UI and Soily's demonstration context. */
export const showcaseInputs = inputs;
export default {
    ...inputs.presentation,
    accountType: 'Farm workspace',
    water: 'Rainfed - no irrigation',
    cropHistory: 'Sunflower (2023), sunflower (2024), winter wheat (2025)',
    soil: 'Loam; entered soil values are unverified inputs',
    status: 'Current farm inputs',
    source: 'Configured starting inputs. Original provenance is preserved in the downloaded data.',
    introduction: "Hi, I'm Soily. I can help you explore your field's climate, compare crop options and calculate returns from your inputs. Your farm details are in Personal state, where you can change or clear them. What would you like to work on?",
    strategies: inputs.presentation.strategies.map(strategy => ({
        ...strategy,
        description: 'A draft sequence to review against your crop history, field conditions and priorities. Use the calculation tools to check inputs and compare scenarios.',
    })),
    limitations: [
        'Entered and assumed values remain editable; they are not verified measurements.',
        'Rotations need crop-calendar, return-interval and cyclic-continuity checks.',
        'NASA POWER provides historical gridded climate, not a forecast or field-station observation.',
        'Gross margins depend on the entered yield, price and cost. Crop scores and erosion estimates need sourced inputs.',
    ],
};
