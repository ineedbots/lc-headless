// Run from an isolated engine working directory; see README.md.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [engineRoot, username = 'navprobe37'] = process.argv.slice(2);
if (!engineRoot) {
    throw new Error('usage: refuse_crossing.mts <289 engine folder> [scratch username]');
}
const config = JSON.parse(fs.readFileSync('data/config/world.json', 'utf8').replace(/^\uFEFF/, ''));
if (config.node.production !== false || config.login.enabled !== false || config.build.liveReload !== false) {
    throw new Error('requires a development engine with local scratch saves and live reload disabled');
}
const source = (file: string) => pathToFileURL(path.resolve(engineRoot, 'src', file)).href;
// Load the normal entry point first, preserving its module initialization order.
await import(source('app.ts'));
const { default: OpLocHandler } = await import(source('network/game/client/handler/OpLocHandler.ts'));
const original = OpLocHandler.prototype.handle;
OpLocHandler.prototype.handle = function(message, player) {
    if (player.username === username && player.level === 0 && message.x === 3217 && message.z === 3218 && message.loc === 1516 && message.op === 1) {
        console.log('ISSUE37_REFUSAL', JSON.stringify({username: player.username, x: message.x, z: message.z, locId: message.loc,
            op: message.op, playerX: player.x, playerZ: player.z, time: Date.now()}));
        player.messageGame('The door is locked.');
        return true;
    }
    return original.call(this, message, player);
};
