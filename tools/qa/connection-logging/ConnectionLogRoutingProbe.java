import java.nio.file.*;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.core.LoggerContext;

/** Private Log4j routing fixture, not a game/mod/agent or actual guest exception. */
public final class ConnectionLogRoutingProbe {
    public static void main(String[] args) throws Exception {
        boolean expectedDebug = Boolean.parseBoolean(args[0]);
        Logger connection = LogManager.getLogger("net.minecraft.network.Connection");
        Logger unrelated = LogManager.getLogger("private.fixture.UnrelatedLogger");
        if (connection.isDebugEnabled() != expectedDebug || unrelated.isDebugEnabled() || connection.isTraceEnabled())
            throw new AssertionError("Unexpected logger-level boundaries");
        Throwable synthetic = new ArrayIndexOutOfBoundsException("PRIVATE SYNTHETIC ROUTING FIXTURE; not a player exception");
        synthetic.setStackTrace(new StackTraceElement[] {
            new StackTraceElement("private.fixture.PacketDecoder", "syntheticDecode", "RoutingFixture.java", 17)
        });
        connection.debug("PRIVATE_CONNECTION_DEBUG_SENTINEL", synthetic);
        connection.trace("PRIVATE_CONNECTION_TRACE_MUST_NOT_BE_WRITTEN");
        unrelated.debug("PRIVATE_UNRELATED_DEBUG_MUST_NOT_BE_WRITTEN");
        unrelated.error("PRIVATE_ERROR_MUST_BE_WRITTEN");
        ((LoggerContext)LogManager.getContext(false)).stop();
        String file = Files.readString(Path.of("logs/latest.log"));
        boolean hasDebug = file.contains("PRIVATE_CONNECTION_DEBUG_SENTINEL");
        boolean hasThrowable = file.contains("PRIVATE SYNTHETIC ROUTING FIXTURE") && file.contains("RoutingFixture.java:17");
        if (hasDebug != expectedDebug || hasThrowable != expectedDebug ||
            file.contains("PRIVATE_UNRELATED_DEBUG_MUST_NOT_BE_WRITTEN") ||
            file.contains("PRIVATE_CONNECTION_TRACE_MUST_NOT_BE_WRITTEN") ||
            !file.contains("PRIVATE_ERROR_MUST_BE_WRITTEN"))
            throw new AssertionError("Incorrect bounded file/exception routing");
        System.out.println("PASS private-native-Log4j-routing expectedConnectionDebug=" + expectedDebug +
            " unrelatedDebug=false trace=false errorPreserved=true syntheticFixtureOnly=true gameStarted=false");
    }
}
